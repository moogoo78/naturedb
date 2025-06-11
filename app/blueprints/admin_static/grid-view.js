(function() {
  'use strict';

  const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  };

  console.log(GRID_INFO);

  let isEdit = null;

  const columns = GRID_INFO.list_display.map( field => {
    let render = null;
    if (GRID_INFO.list_display_rules[field] && GRID_INFO.list_display_rules[field][0] === 'clean') {
      render = function (record) {
        return record[`${field}__clean`];
      };
    }/* else if (GRID_INFO.list_display_rules[field] && GRID_INFO.list_display_rules[field][0] === 'render') {
      render = GRID_INFO.list_display_rules[field][1];
    }*/
    if (GRID_INFO.list_display_rules[field] && GRID_INFO.list_display_rules[field][0] === 'format') {
      render = function (record) {
        return record[`${field}_raw`].strftime('%Y-%m-%d');
      };
    }
    return {
      field: field,
      text: GRID_INFO.fields[field].label,
      sortable: true,
      render: render,
      type: GRID_INFO.fields[field].type === 'date' ? 'date' : 'text'
    };
  });

  const searches = GRID_INFO.list_display.map( field => {
    let render = null;
    if (GRID_INFO.list_display_rules[field] && GRID_INFO.list_display_rules[field][0] === 'clean') {
      render = function (record) {
        return record[`${field}__clean`];
      };
    }
    return {
      field: field,
      label: GRID_INFO.fields[field].label,
      type: 'text',
    };
  });

  let formFields = [{
    field: 'recid',
    type: 'text',
    html: {
      label: 'ID',
      attr: 'size="10" readonly'
    }
  }];
  if (GRID_INFO.form_layout) {
    for (let rowFields of GRID_INFO.form_layout) {
      for (let field of rowFields) {
        let formType = 'text';
        if (GRID_INFO.fields[field].type === 'boolean') {
          formType = 'checkbox';
        } else if (GRID_INFO.fields[field].type === 'select') {
          formType = 'list';
        } else if (GRID_INFO.fields[field].type === 'html') {
          formType = 'textarea';
        } else if (GRID_INFO.fields[field].type === 'date') {
          formType = 'date';
        }
        let attr = 'size="50%"';
        if (GRID_INFO.fields[field].attr) {
          attr = GRID_INFO.fields[field].attr;
        }

        let fieldInfo = {
          field: field,
          type: formType,
          html: {
            label: GRID_INFO.fields[field].label,
            attr: attr,
          }
        };
        if (formType === 'list') {
          if (typeof GRID_INFO.fields[field].options[0] === 'string') {
            fieldInfo.options = {
              items: GRID_INFO.fields[field].options.map( x => ({id: x, text: x}))
            };
          } else {
            fieldInfo.options = {
              items: GRID_INFO.fields[field].options
            };
          }
        }
        formFields.push(fieldInfo);
      }
    }
  } else {
    for (let field in GRID_INFO.fields) {
      let formType = 'text';
      if (GRID_INFO.fields[field].type === 'boolean') {
        formType = 'checkbox';
      } else if (GRID_INFO.fields[field].type === 'select') {
        formType = 'list';
      } else if (GRID_INFO.fields[field].type === 'html') {
        formType = 'textarea';
      } else if (GRID_INFO.fields[field].type === 'date') {
        formType = 'date';
      }
      let attr = 'size="50%"';
      if (GRID_INFO.fields[field].attr) {
        attr = GRID_INFO.fields[field].attr;
      }
      let render = null;
      if (GRID_INFO.list_display_rules[field] && GRID_INFO.list_display_rules[field][0] === 'clean') {
        render = function (record) {
          return record[`${field}__clean`];
        };
      }
      let fieldInfo = {
        field: field,
        type: formType,
        html: {
          label: GRID_INFO.fields[field].label,
          attr: attr,
        }
      };
      if (render) {
        fieldInfo.render = render;
      }
      if (formType === 'list') {
        if (typeof GRID_INFO.fields[field].options[0] === 'string') {
          fieldInfo.options = {
            items: GRID_INFO.fields[field].options.map( x => ({id: x, text: x}))
          };
        } else {
          fieldInfo.options = {
            items: GRID_INFO.fields[field].options
          };
        }
      } else if (isCleanHtml) {
        // For clean HTML fields, we want to show the raw content in the form
        fieldInfo.type = 'textarea';
        fieldInfo.html.attr = 'rows="5" cols="50"';
      }
      formFields.push(fieldInfo);
    }
  }

  if (GRID_INFO.relations) {
    for (let field in GRID_INFO.relations) {
      formFields.push({
        field: `relation__${field}`,
        type: 'textarea',
        html: {
          label: GRID_INFO.relations[field].label,
          attr: 'size="50%" readonly',
        }
      });
    }
  }

  console.log(formFields, columns);
  let grid_config = {
    name: 'grid',
    header: GRID_INFO.label,
    reorderRows: false,
    multiSelect: false,
    url: `/admin/api/1/${GRID_INFO.resource_name}`,
    autoLoad: false,
    show: {
        header: true,
        footer: true,
        toolbar: true,
        lineNumbers: true,
        toolbarAdd: true,
        toolbarEdit: true,
        toolbarDelete: true,
    },
    columns: columns,
    searches: searches,
    onAdd: function (event) {
      w2ui.form.clear();
      w2ui.form.header = '新增';
      w2ui.form.refresh();

      // disable relation buttons
      for (let field in GRID_INFO.relations) {
        form.toolbar.enable(`btn-${field}`);
      }
      toggleEdit(true);
    },
    onClick(event) {
      event.done(() => {
          let sel = this.getSelection();
          w2ui.form.header = '編輯';
          if (sel.length == 1) {
              w2ui.form.recid = sel[0]
              w2ui.form.record = w2utils.extend({}, this.get(sel[0]))
              w2ui.form.refresh()
          } else {
              w2ui.form.clear()
          }

        for (let field in GRID_INFO.relations) {
          if (!w2ui.form.getValue('relation__taxon')) {
            w2ui.form.toolbar.enable(`btn-${field}`);
          } else {
            w2ui.form.toolbar.disable(`btn-${field}`);
          }
        }
      })
    },
    onDblClick(event) {
      event.done(() => {
          let sel = this.getSelection();
          w2ui.form.header = '編輯';
          if (sel.length == 1) {
              w2ui.form.recid = sel[0]
              w2ui.form.record = w2utils.extend({}, this.get(sel[0]))
              w2ui.form.refresh()
          }
          // enable relation buttons
          for (let field in GRID_INFO.relations) {
            w2ui.form.toolbar.disable(`btn-${field}`);
          }
          toggleEdit(true);
      })
    },
    onEdit: function (event) {
      toggleEdit(!isEdit);
      w2ui.form.header = '編輯';
    },
    onDelete: function (event) {
      event.preventDefault();
      w2confirm('確定要刪除嗎？')
      .yes(() => {
        let sel = this.getSelection();
        fetch(`/admin/api/1/${GRID_INFO.resource_name}/${sel[0]}`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
          },
        }).then(response => {
          if (response.ok) {
            grid.reload();
          }
          return response.json();
        }).then(data => {
          console.log(data);
        });
      });
    },
    onLoad: async function(event) {
      await event.complete;
      console.log(this.records);
      //this.records.forEach(record => {
      //  console.log(record);
      //});
      //this.refresh();
      //return event.done();
    }
  };

  function toggleEdit(toEdit) {
    if (toEdit === undefined) {
      toEdit = !isEdit;
    }
    isEdit = toEdit;
    if (isEdit) {
      w2ui.layout.show('main');
      w2ui.layout.set('left', { size: '50%'});
    } else {
      w2ui.layout.hide('main');
      w2ui.layout.set('left', { size: '100%'});
    }
  }

  let form_config = {
    header: '編輯',
    name: 'form',
    fields: formFields,
    actions: {
        Reset() {
            this.clear()
        },
        Save() {
            let errors = this.validate()
            if (errors.length > 0) return

            let url = '';
            if (this.recid) {
              url = `/admin/api/1/${GRID_INFO.resource_name}/${this.recid}`
            } else {
                url = `/admin/api/1/${GRID_INFO.resource_name}`
            }
            fetch(url, {
                method: this.recid ? 'PATCH' : 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': getCookie('csrf_access_token'),
                },
                body: JSON.stringify(this.getCleanRecord()),
            }).then(response => {
                if (response.ok) {
                    w2ui.grid.reload();
                    this.clear();
                    toggleEdit(false);
                }
                return response.json();
            }).then(data => {
              console.log(data);
              });
            /*
            if (this.recid == 0) {
                //grid.add(w2utils.extend(this.record, { recid: grid.records.length + 2 }))
                grid.selectNone()
                this.clear()
            } else {
                grid.set(this.recid, this.record)
                grid.selectNone()
                this.clear()
            } 
            */
        }
    }
  };
  // Hard-Code
  const TAXON_RANKS = ['family', 'genus', 'species'];

  if (GRID_INFO.relations && Object.keys(GRID_INFO.relations).length > 0) {
    let toolbarItems = [];
    let relType = '';
    for (let field in GRID_INFO.relations) {
      toolbarItems.push({
        id: 'btn-' + field,
        type: 'button',
        text: `設定 ${GRID_INFO.relations[field].label}`,
        img: 'w2ui-icon-info',
      });
      relType = field;
    }

    form_config.toolbar = {
      items: toolbarItems,
      onClick(event) {
        let currentRank = w2ui.form.getValue('rank');
        if (currentRank === undefined) {
          w2alert('必須選擇rank');
        } else if (TAXON_RANKS.indexOf(currentRank.id) === 0) {
          w2alert('已經是最高階層');
        } else {
          openRelationForm(relType, currentRank.id);
        }
      }
    }
  }

  let layout = new w2layout({
    name: 'layout',
    box: '#layout',
    padding: 4,
    panels: [
      { type: 'left', size: '100%', resizable: true},
      { type: 'main', resizable: true, style: 'overflow: hidden'},
  ]
  });

  let grid = new w2grid(grid_config);
  let form = new w2form(form_config);

  layout.html('left', grid);
  layout.html('main', form);
  toggleEdit(false);

  async function openRelationForm(relType, currentRankId) {
    // TODO here, only one relation is allowed, and dropdown = cascade
    //let resp = await fetch(`/admin/api/relation/${relType}?item_id=${grid.getSelection()[0]}&action=get_form_list`);
    
    let resp = await fetch(`/admin/api/relation/${relType}?action=get_form_list`);
    let data = await resp.json();
    let relFormFields = [];
    for ( let i=0; i < TAXON_RANKS.indexOf(currentRankId); i++) {
      let item = data.form_list[i];
      relFormFields.push({
        field: item.name,
        type: 'list',
        html: { label: item.label },
        options: {
          items: item.options,
        },
      });
    }
    //console.log('relFormFields:', relFormFields);
    if (w2ui.relForm) {
      w2ui.relForm.destroy();
    }
    w2ui.relForm = new w2form({
      name: 'relForm',
      style: 'border: 0px; background-color: transparent;',
      fields: relFormFields,
      actions: {
        Ok(event) {
          const higherTaxa = [];
          for (const [key, value] of Object.entries(this.record)) {
            higherTaxa.push(`${key}:${value.id}:${value.text}`);
          }
          w2ui.form.setValue('relation__taxon', higherTaxa.join('|'));
          w2ui.form.refresh();
          w2popup.close();
        },
        //Reset() { this.clear() },
        /*
        Save() {
          this.validate();
          w2confirm('確定要修改階層嗎？')
            .yes(() => {
              //console.log('save', grid.getSelection()[0], this.record);
              fetch(`/admin/api/relation/${relType}?item_id=${grid.getSelection()[0]}`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'X-CSRF-TOKEN': getCookie('csrf_access_token'),
                },
                body: JSON.stringify({item_id: grid.getSelection()[0], data: this.record}),
              }).then(response => {
                if (response.ok) {
                }
                return response.json();
              }).then(data => {
                if (data.message === 'ok'){
                  document.location.reload();
                }
              });
           });
        },
        */
      }
    });

    let recordValues = {};
    for(let i = 0; i < relFormFields.length; i++) {
      recordValues[relFormFields[i].field] = data.form_list[i].value;
    }

    // this is how to set the form values
    w2ui.relForm.record = recordValues;
    w2ui.relForm.refresh();

    w2ui.relForm.on('change', async function(e) {
      let topRank = relFormFields[0].field;
      if (w2ui.relForm.fields.length > 1) {
        if (e.target === topRank) {
          relFormFields.forEach( x => {
            if (x['field'] !== topRank) {
              w2ui.relForm.setValue(x['field'], '');
            }
          });
          let value = w2ui.relForm.getValue(topRank);
          let nextRank = relFormFields[1].field;
          let resp = await fetch(`/admin/api/relation/${relType}?item_id=${value.id}&action=get_children`);
          let data = await resp.json();
          const nextRankField = {
            field: nextRank,
            type: 'list',
            options: {
                items: data.options
            }
          };

          // Replace the field
          w2ui.relForm.fields = w2ui.relForm.fields.map(field => {
              if (field.field === nextRank) {
                  return nextRankField;
              }
              return field;
          });
          // must set, or will not update
          setTimeout(() => {
            w2ui.relForm.render('#form');
          }, 100);
        }
      }
    });

    w2popup.open({
      title   : `設定: ${GRID_INFO.relations[relType].label}`,
      body    : '<div id="form" style="width: 100%; height: 100%;"></div>',
      style   : 'padding: 15px 0px 0px 0px',
      width   : 500,
      height  : 280,
      //showMax : true,
      async onToggle(event) {
          await event.complete
          w2ui.relForm.resize();
      }
  })
  .then((event) => {
      w2ui.relForm.render('#form') // cannot change id !!
  });

  }

})();
