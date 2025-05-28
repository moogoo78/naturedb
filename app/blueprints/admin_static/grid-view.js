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
    return {
      field: field,
      text: GRID_INFO.fields[field].label,
      sortable: true
    };
  });

  const searches = GRID_INFO.list_filter.map( field => {
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
  for (let field in GRID_INFO.fields) {
    let formType = 'text';
    if (GRID_INFO.fields[field].type == 'boolean') {
      formType = 'checkbox';
    }
    else if (GRID_INFO.fields[field].type == 'select') {
      formType = 'list';
    }

    let attr = 'size="50%"';
    let fieldInfo = {
      field: field,
      type: formType,
      html: {
        label: GRID_INFO.fields[field].label,
        attr: attr,
      }
    }

    if (formType == 'list') {
      fieldInfo.options = {
        items: GRID_INFO.fields[field].options.map( x => ({id: x, text: x}))
      }
    }

    formFields.push(fieldInfo);
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
    searches: searches,
    columns: columns,
    onAdd: function (event) {
      w2ui.form.clear();
      w2ui.form.header = '新增';
      w2ui.form.refresh();

      // disable relation buttons
      for (let field in GRID_INFO.relations) {
        form.toolbar.disable(`btn-${field}`);
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
          // enable relation buttons
          for (let field in GRID_INFO.relations) {
            w2ui.form.toolbar.enable(`btn-${field}`);
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
            w2ui.form.toolbar.enable(`btn-${field}`);
          }          
          toggleEdit(true);
      })
    },
    onEdit: function (event) {
      toggleEdit(true);
      w2ui.form.header = '編輯';
      toggleEdit(true);      
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
  /*
          { field: 'recid', type: 'text', html: { label: 'ID', attr: 'size="10" readonly' } },
        { field: 'fname', type: 'text', required: true, html: { label: 'First Name', attr: 'size="40" maxlength="40"' } },
        { field: 'lname', type: 'text', required: true, html: { label: 'Last Name', attr: 'size="40" maxlength="40"' } },
        { field: 'email', type: 'email', html: { label: 'Email', attr: 'size="30"' } },
        { field: 'sdate', type: 'date', html: { label: 'Date', attr: 'size="10"' } }
   */
  
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

  if (Object.keys(GRID_INFO.relations).length > 0) {
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
        openRelationForm(relType, toolbarItems);
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
  let form = new w2form(form_config)

  layout.html('left', grid);
  layout.html('main', form);
  toggleEdit(false);

  async function openRelationForm(relType) {
    // TODO here, only one relation is allowed, and dropdown = cascade
    let resp = await fetch(`/admin/api/relation/${relType}?item_id=${grid.getSelection()[0]}&action=get_form_list`);
    let data = await resp.json();
    let relFormFields = data.form_list.map( item => {
      return {
        field: item.name, 
        type: 'list',
        html: { label: item.label },
        options: { 
          items: item.options,
        },
      };
    });

    if (w2ui.relForm) {
      w2ui.relForm.destroy();
    }
    w2ui.relForm = new w2form({
      name: 'relForm',
      style: 'border: 0px; background-color: transparent;',
      fields: relFormFields,
      actions: {
        Reset() { this.clear() },
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
