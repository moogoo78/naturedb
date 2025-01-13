/*
 * utils
 */
const fetchData = (endpoint) => {
  const headers = {
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8",
    'X-Requested-With': 'XMLHttpRequest'
  };
  return fetch(endpoint, {
    method: "GET",
    cache: "no-cache",
    credentials: "same-origin",
    headers: headers,
  })
    .then(response => response.json())
    .then(json => {
      return Promise.resolve(json);
    })
    .catch(error => console.log(error));
};

const convertDDToDMS = (dd) => {
  /* arguments: decimal degree
   */
  const direction = (parseFloat(dd) >=0) ? 1 : -1;
  const ddFloat = Math.abs(parseFloat(dd));
  const degree = Math.floor(ddFloat);
  const minuteFloat = (ddFloat - degree) * 60;
  const minute = Math.floor(minuteFloat);
  const secondFloat = ((minuteFloat - minute) * 60);
  const second = parseFloat(secondFloat.toFixed(4));
    //console.log(dd, ddFloat,minuteFloat, [degree, minute, second]);
  return [direction, degree, minute, second];
};

const convertDMSToDD = (ddms) => {
  /* arguments: degree, minute, second
   */
  // console.log(ddms);
  return ddms[0] * (parseFloat(ddms[1]) + parseFloat(ddms[2]) / 60 + parseFloat(ddms[3]) / 3600);
}

const findItem = (key, options, isAll=false) => {
  let item = options.find( x => x[0] === key);
  if (item) {
    return (isAll) ? item : item[1];
  } else {
    return '';
  }
};

const onSelect2Change = (elem, initVal) => {
  //console.log(elem.value, initVal);
  if (elem.value.toString() === initVal.toString()) {
    $(elem).siblings('.select2').children('.selection').children('.select2-selection').css('border-color', '');
    $(elem).siblings('.select2').children('.selection').children('.select2-selection').children('.select2-selection__rendered').css('color', '');
  } else {
    $(elem).siblings('.select2').children('.selection').children('.select2-selection').css('border-color', '#32d296');
    $(elem).siblings('.select2').children('.selection').children('.select2-selection').children('.select2-selection__rendered').css('color', '#32d296');
  }
};

const onSelect2ChangeArr = (elem, initVal) => {
  //console.log($(`#${elem.id}`).val(), initVal);
  let initValSet = new Set(initVal.map(x => (x.toString())));
  let valSet = new Set($(`#${elem.id}`).val().map( x => (x.toString())));
  if (valSet.difference(initValSet).size === 0) {
    $(elem).siblings('.select2').children('.selection').children('.select2-selection').css('border-color', '');
    $(elem).siblings('.select2').children('.selection').children('.select2-selection').children('.select2-selection__rendered').css('color', '');
  } else {
    $(elem).siblings('.select2').children('.selection').children('.select2-selection').css('border-color', '#32d296');
    $(elem).siblings('.select2').children('.selection').children('.select2-selection').children('.select2-selection__rendered').css('color', '#32d296');
  }
};

const makeOptions = (element, options, value='', custom=false) => {
  element[0] = new Option("{{ _('-- 選澤 --') }}", '', false, false);
  let selected = false;
  options.forEach( (opt, idx) => {
    //console.log(value, opt.id);
    if (value && value.toString() === opt.id.toString()){
      element[idx+1] = new Option(opt.text, opt.id, true, true);
      selected = true;
    } else {
      element[idx+1] = new Option(opt.text, opt.id, false, false);
    }
  });
  if (custom === true && selected === false) {
    let m = /\[(.*)\]__(.*)__([0-9]*)/.exec(value);
    if (m) {
      element[options.length+1] = new Option(m[2], value, true, true);
    }
  }
};

const genRand = () => {
  let nowSecs = parseInt(Date.now().toString().slice(-5)).toString(16); // 4 char
  let nowRand = Math.random().toString(16).substring(2, 5); // 3 char
  return `${nowSecs}${nowRand}`;
};

/**
 * via: https://stackoverflow.com/a/15724300/644070
 */
const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
};

/*
 * jquery ready
 */
$( document ).ready(function() {
  const fetchUrls = [
    '/admin/api/collections/{{ collection_id }}/options',
  ];

  const collectionId = parseInt({{ collection_id }});
  {% if record_id %}
  const recordId = parseInt({{ record_id }});
  fetchUrls.push('/admin/api/records/{{ record_id }}');
  {% else %}
  const recordId = null;
  {% endif %}
  //console.log(recordId, collectionId);

  const fetchNamedAreaOptions = async (area_class_id, parent_id) => {
    const filtr = {
      parent_id: parent_id,
      area_class_id: area_class_id,
    };
    const url = `/api/v1/named-areas?filter=${JSON.stringify(filtr)}`;
    const res = await fetchData(url);
    return res.data.map( x => ({ id: x.id, text: x.display_name }));
  };

  const deleteRecord = async () => {
    let url = `${document.location.origin}/admin/api/records/{{ record_id }}`;
    return fetch(url, {
      method: "DELETE",
      headers: {
        "X-CSRF-TOKEN": getCookie("csrf_access_token"),
      },
    })
      .then(response => {
        return null
      });

  };
  const saveRecord = (payload, next_url='') => {
    let method = 'POST';
    let url = `${document.location.origin}/admin/api/records`;
    if (recordId) {
      url = `${url}/${recordId}`;
      method = 'PATCH';
    }

    fetch(url, {
      method: method,
      //mode: "cors", // no-cors, *cors, same-origin
      cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
      credentials: "same-origin", // include, *same-origin, omit
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-TOKEN": getCookie("csrf_access_token"),
        // 'Content-Type': 'application/x-www-form-urlencoded',
      },
      redirect: "follow", // manual, *follow, error
      referrerPolicy: "no-referrer",
      body: JSON.stringify(payload),
    })
      .then(response => response.json())
      .then(result => {
        UIkit.notification('已儲存', {timeout: 1000});
        console.log(result);
        if (next_url) {
          const timeoutID = window.setTimeout(( () => {
            if  (next_url === 'result' && result.next_url) {
              next_url = result.next_url; //change to record id url
            }

            if (next_url === '.') {
              location.reload();
            } else {
              location.replace(next_url);
            }
            }), 1000);
        }
      })
      .catch(error => {
        alert(error);
      });
  };

  const preparePayload = (options) => {

    if (options._phase1) {
      const rawElem = document.querySelectorAll('.ndb-phase1-raw');
      let payload = {_phase1: {}};
      rawElem.forEach( x => {
        payload._phase1[x.id.replace('raw-', '').replace('-id', '')] = x.value || '';
      });
      return payload;
    }

    let payload = {
      collection_id: {{ collection_id }},
      assertions: {},
      identifications: [],
      units: {},
    };
    payload.collector_id = document.getElementById('collector-id').value;
    payload.record_groups = $('#record_groups-id').val();
    payload.named_areas = {
      COUNTRY: document.getElementById('COUNTRY-id').value,
      ADM1: document.getElementById('ADM1-id').value,
      ADM2: document.getElementById('ADM2-id').value,
      ADM3: document.getElementById('ADM3-id').value,
    };
    for (const [areaClass, data] of Object.entries(options.named_areas)) {
      if (areaClass !== 'COUNTRY') {
        payload.named_areas[areaClass] = document.getElementById(`${areaClass}-id`).value;
      }
    }
    options._record_fields.forEach( field => {
      payload[field] = document.getElementById(`${field}-id`).value;
    });
    options.assertion_type_record_list.forEach( x => {
      payload.assertions[x.name] = document.getElementById(`record-assertion-${x.name}-id`).value;
    });
    let ids = document.querySelectorAll('.identification-box');
    ids.forEach( x => {
      let idx = x.dataset.index;
      let idPayload = {};
      options._identification_fields.concat(['id']).forEach( field => {
        idPayload[field] = x.querySelector(`#identification-${idx}-${field}-id`).value;
      });
      idPayload.taxon_id = x.querySelector(`#identification-${idx}-taxon-id`).value;
      idPayload.identifier_id = x.querySelector(`#identification-${idx}-identifier-id`).value;
      payload.identifications.push(idPayload);
    });

    document.querySelectorAll('.unit-box').forEach( x => {
      let idx = x.dataset.index;
      let unitPayload = { assertions: {}, annotations: {} };
      options._unit_fields.concat(['id', 'tracking_tags__rfid']).forEach( field => {
        unitPayload[field] = x.querySelector(`#unit-${idx}-${field}-id`).value;
      });
      options.assertion_type_unit_list.forEach( x => {
        unitPayload.assertions[x.name] = document.getElementById(`unit-${idx}-assertion-${x.name}-id`).value;
      });
      options.annotation_type_unit_list.forEach( x => {
        unitPayload.annotations[x.name] = document.getElementById(`unit-${idx}-annotation-${x.name}-id`).value;
      });
      payload.units[unitPayload.id] = unitPayload;
    });

    return payload;
  };

  const renderAttributes = (containerId, attributes, prefix, values={}, parentId=null) => {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    for (let item of attributes) {
      let assertion = document.getElementById('template-widget').content.cloneNode(true);
      let label = assertion.querySelector('label');
      label.textContent =  item.label;
      label.setAttribute('for', item.name);
      let itemId = `${prefix}-${item.name}-id`;
      let itemElement = null;
      let val = values[item.name]?.value || '';

      if (item.input_type === 'free') {
        itemElement = document.getElementById('template-widget-select2').content.cloneNode(true);
        let s = itemElement.querySelector('select');
        s.id = itemId;
        let idPrefix = '';
        if (values[item.name]) {
          idPrefix = `[${values[item.name].id}]`;
          val = `${idPrefix}__${values[item.name].value}__${values[item.name].option_id || ''}`;
        }
        let options = item.options.map( x => {
          return {
            id: `${idPrefix}__${x.value}__${x.id}`,
            text: x.display_name,
          };
        });

        makeOptions(s, options, val, true);

        let conf = {
          width: '100%',
          tags: true,
        };
        if (parentId) {
          conf = {
            ...conf,
            dropdownParent: $(`#${parentId}`),
          };
        }
        $(s).select2(conf).on('change', (e) => {
          onSelect2Change(e.target, val);
        });
      } else if (item.input_type === 'select') {
        itemElement = document.createElement('select');
        itemElement.classList.add('uk-select');
        itemElement.id = itemId;
        const options = item.options.map( x => ({ id: x[0], text: x[1]}));
        makeOptions(itemElement, options, val);
      } else if (item.input_type === 'input') {
        itemElement = document.createElement('input');
        itemElement.classList.add('uk-input');
        itemElement.id = itemId;
        itemElement.value = val;
        itemElement.oninput = (e, key=item.name) => {
          if (val === e.target.value) {
            e.target.classList.remove('uk-form-success');
          } else {
            e.target.classList.add('uk-form-success');
          }
        };
      } else if (item.input_type === 'input-date') {
        itemElement = document.createElement('input');
        itemElement.classList.add('uk-input');
        itemElement.setAttribute('type', 'date');
        itemElement.id = itemId;
        itemElement.value = (values[item.name]) ? values[item.name].value : '';
        itemElement.onchange = (e) => {
          if (val === e.target.value) {
            e.target.classList.remove('uk-form-success');
          } else {
            e.target.classList.add('uk-form-success');
          }
        };
      } else if(item.input_type === 'text') {
        itemElement = document.createElement('textarea');
        itemElement.classList.add('uk-textarea');
        itemElement.id = itemId;
        itemElement.textContent = (values[item.name]) ? values[item.name].value : '';
        itemElement.oninput = (e) => {
          if (val === e.target.value) {
            e.target.classList.remove('uk-form-success');
          } else {
            e.target.classList.add('uk-form-success');
          }
        };
      } else if (item.input_type === 'checkbox') {
        itemElement = document.createElement('input');
        itemElement.classList.add('uk-checkbox');
        itemElement.setAttribute('type', 'checkbox');
        itemElement.id = itemId;
        itemElement.value = val;
        if (val) {
          itemElement.setAttribute('checked', 'checked');
        } else {
          itemElement.removeAttribute('checked');
        }
        itemElement.onchange = (e) => {
          if (e.target.checked === false) {
            itemElement.value = '';
          } else {
            itemElement.value = 'on';
          }
        };
      }
      assertion.querySelector('.uk-form-controls').appendChild(itemElement);
      container.appendChild(assertion);
    }
  };

  const initNamedAreas = async (named_areas, area_classes) => {
    let container = document.getElementById('area-class-container');

    for(let name in area_classes) {
      let widgetId = `${name}-id`;
      let s = null;
      if ( name !== 'COUNTRY') {
        let widget = document.getElementById('template-widget').content.cloneNode(true);
        let wrapper = widget.querySelector('.widget-wrapper');
        //wrapper.classList.remove('uk-width-1-1@s');
        //wrapper.classList.add('uk-width-1-2@s');
        let label = widget.querySelector('label');
        label.textContent = area_classes[name].label;
        label.setAttribute('for', '');
        let select2 = document.getElementById('template-widget-select2').content.cloneNode(true);
        s = select2.querySelector('select');
        s.id = widgetId;
        widget.querySelector('.uk-form-controls').appendChild(select2);
        container.appendChild(widget);
      } else {
        s = document.getElementById('COUNTRY-id');
      }
      //$(`#${widgetId}`).select2({data: options}).on('change', (e, v=val) => onSelect2Change(e, v));

      let counter = 0;
      s[0] = new Option("{{ _('-- 選澤 --') }}", '', false, false);
      area_classes[name].options.forEach( x => {
        counter += 1;
        s[counter] = new Option(x.display_name, x.id, false, false);
      });

      if ( name !== 'COUNTRY') {
        if (named_areas[name]) {
          $(`#${widgetId}`).val(named_areas[name].id).select2();
        } else {
          $(`#${widgetId}`).select2();
        }
      }
    }

    if (named_areas.COUNTRY) {
      $('#COUNTRY-id').val(named_areas.COUNTRY.id).select2();
      const options = await fetchNamedAreaOptions(8, named_areas.COUNTRY.id);
      $('#ADM1-id').html('').select2({data: options}).val('');
    } else {
      $('#COUNTRY-id').select2();
    }

    if (named_areas.ADM1) {
      $('#ADM1-id').val(named_areas.ADM1.id).select2();
      const options = await fetchNamedAreaOptions(9, named_areas.ADM1.id);
      $('#ADM2-id').html('').select2({data: options}).val('').select2();
    } else {
      $('#ADM1-id').select2();
    }

    if (named_areas.ADM2) {
      $('#ADM2-id').val(named_areas.ADM2.id).select2();
      const options = await fetchNamedAreaOptions(10, named_areas.ADM2.id);
      $('#ADM3-id').html('').select2({data: options}).val('').select2();
    } else {
      $('#ADM2-id').select2();
    }
    if (named_areas.ADM3) {
      $('#ADM3-id').val(named_areas.ADM3.id).select2();
    } else {
      $('#ADM3-id').select2();
    }

    // set named areas
    $('#COUNTRY-id').on('change', async (e) => {
      $('#ADM1-id').empty();
      $('#ADM2-id').empty();
      $('#ADM3-id').empty();
      if (e.target.value) {
        const options = await fetchNamedAreaOptions(8, e.target.value);
        $('#ADM1-id').select2({data: options}).val('').select2();
        onSelect2Change(e.target, named_areas.COUNTRY?.id || '');
      }
    });
    $('#ADM1-id').on('change', async (e) => {
      $('#ADM2-id').empty();
      $('#ADM3-id').empty();
      if (e.target.value) {
        const options = await fetchNamedAreaOptions(9, e.target.value);
        $('#ADM2-id').select2({data: options}).val('').select2();
        onSelect2Change(e.target, named_areas.ADM1?.id || '');
      }
    });
    $('#ADM2-id').on('change', async (e) => {
      $('#ADM3-id').empty();
      if (e.target.value) {
        const options = await fetchNamedAreaOptions(10, e.target.value);
        $('#ADM3-id').select2({data: options}).val('').select2();
        onSelect2Change(e.target, named_areas.ADM2?.id || '');
      }
    });

    $('#ADM3-id').on('change', (e) => {
      onSelect2Change(e.target, named_areas.ADM3?.id || '');
    });

  };

  const initIdentifications = (fields, identifiers, idValues) => {
    let idContainer = document.getElementById('identification-container');

    const createIdentificationCard = (values) => {
      let index = genRand();
      let idCard = document.getElementById('template-identification').content.cloneNode(true);

      idCard.children[0].setAttribute('id', `identification-${index}-wrapper`);
      idCard.children[0].classList.add('identification-box');
      idCard.children[0].dataset.index = index;
      idCard.querySelector('.uk-label-success').textContent = index;

      // set element id
      fields.concat(['id']).forEach( field => {
        let elem = idCard.querySelector(`#${field}-id`);
        elem.id = `identification-${index}-${field}-id`;
        elem.value = values[field] || '';
      });

      // identifier
      let identifier = idCard.querySelector('#identifier-id');
      identifier.id = `identification-${index}-identifier-id`;
      //makeOptions(elem, identifiers, v);
      $(identifier).select2({
        data: identifiers,
        width: '100%',
      }).val(values.identifier?.id).trigger('change');

      // taxon
      let taxon = idCard.querySelector('#taxon-id');
      taxon.id = `identification-${index}-taxon-id`;
      let data = (values.taxon) ? [{id: values.taxon.id, text: values.taxon.display_name}] : [];
      $(taxon).select2({
        width: '100%',
        ajax: {
          url: `/api/v1/taxa`,
          //dataType: 'json',
          delay: 250,
          data: function (params) {
            if (params?.term?.length >= 1) {
              var query = {
                filter: JSON.stringify({q: params.term}),
              };
              return query;
            }
          },
          processResults: function (data) {
            return {
              results: data.data.map( x => ({id: x.id, text: x.display_name}))
            };
          }
        },
        data: data,
      });

      let deleteButton = idCard.querySelector('#delete-button-id');
      deleteButton.id = `identification-${index}-delete-button-id`;
      deleteButton.dataset.index = index;
      deleteButton.onclick = (e) => {
        if (confirm("{{ _('確定刪除?')}}")) {
          let elem = document.getElementById(`identification-${e.target.dataset.index}-wrapper`);
          idContainer.removeChild(elem);
        }
      };
      idContainer.appendChild(idCard);
    }; // end of createIdentificationCard

    document.getElementById('identification-add-button').onclick = () => {
      createIdentificationCard({});
    };
    for (let values of idValues) {
      createIdentificationCard(values);
    }

    if (idValues.length > 0 && idValues[0].taxon) {
      let lastId = document.getElementById('last_identification-id');
      if (idValues[0].identifier) {
        lastId.setAttribute('value', `${idValues[0].taxon.display_name} | ${idValues[0].identifier.display_name}`);
      } else {
        lastId.textContent = `${idValues[0].taxon.display_name}`;
      }
    }
  };

  const initUnits = (allOptions, initUnitValues) => {
    let unitContainer = document.getElementById('unit-container');

    const createUnit = (unit) => {
      let index = genRand();

      const clone = document.getElementById('template-unit-card').content.cloneNode(true);
      const clone2 = document.getElementById('template-unit-modal').content.cloneNode(true);
      let unitCard = clone.children[0];
      let unitModal = clone2.children[0];

      // unitCard
      unitCard.id = `unit-${index}-wrapper`;
      unitCard.dataset.index = index;

      let cardKindOfUnit = unitCard.querySelector('#card-kind-of-unit');
      cardKindOfUnit.id = `unit-${index}-card-kind-of-unit`;
      let kindOfUnitStr = findItem(unit.kind_of_unit, allOptions.unit_kind_of_unit);
      if (unit.parent_id) {
        cardKindOfUnit.innerHTML = `${kindOfUnitStr} ↰<br>Unit: ${unit.parent_id}`;
      } else {
        cardKindOfUnit.textContent = kindOfUnitStr;
      }

      if (unit.basis_of_record === '' || unit.basis_of_record === 'PreservedSpecimen') {
        unitCard.classList.remove('other-card');
        unitCard.classList.add('preserved-specimen-card');
        let cardCat = unitCard.querySelector('.cat-txt');
        cardCat.id = `unit-${index}-card-cat-txt`;
        cardCat.textContent = 'PreservedSpecimen';
      } else if (unit.basis_of_record === 'LivingSpecimen') {
        unitCard.classList.remove('other-card');
        unitCard.classList.add('living-specimen-card');
        let cardCat = unitCard.querySelector('.cat-txt');
        cardCat.id = `unit-${index}-card-cat-txt`;
        cardCat.textContent = 'LivingSpecimen';
      } else if (unit.basis_of_record === 'MaterialSample') {
        unitCard.classList.remove('other-card');
        unitCard.classList.add('material-sample-card');
        let cardCat = unitCard.querySelector('.cat-txt');
        cardCat.id = `unit-${index}-card-cat-txt`;
        cardCat.textContent = 'MaterialSample';
      }
      let cardMuted = unitCard.querySelector('#card-muted');
      cardMuted.id = `unit-${index}-card-muted`;
      cardMuted.classList.add('uk-text-success');
      cardMuted.textContent = findItem(unit.pub_status, allOptions.unit_pub_status);
      let cardTopIcon = unitCard.querySelector('#card-top-icon');
      if (unit.pub_status === 'P') {
        cardTopIcon.classList.add('uk-text-success');
      } else {
        cardTopIcon.classList.add('uk-hidden');
      }

      let cardUnitId = unitCard.querySelector('#card-unit-id');
      cardUnitId.id = `unit-${index}-card-unit-id`;
      cardUnitId.textContent = unit.id;

      let cardImg = unitCard.querySelector('#card-img');
      cardImg.id = `unit-${index}-card-img`;
      if (unit.image_url) {
        cardImg.setAttribute('src', unit.image_url);
      }

      let cardCatalogNumber = unitCard.querySelector('#card-catalog-number');
      cardCatalogNumber.id = `unit-${index}-card-catalog-number`;
      cardCatalogNumber.textContent = `${unit.accession_number}` || '';
      unitContainer.appendChild(unitCard);

      let imgToggle = unitCard.querySelector('#card-img-toggle');
      imgToggle.id = `unit-${index}-card-img-toggle`;
      imgToggle.dataset.img = unit.image_url;
      imgToggle.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        let bigimg = e.currentTarget.dataset.img.replace('-m.', '-o.');
        document.querySelector('#modal-specimen-image').querySelector('img').setAttribute('src', bigimg);
      };

      let deleteBtn = unitCard.querySelector('#card-delete-button');
      deleteBtn.id = `unit-${index}-card-delete-button`;
      deleteBtn.dataset.index = index;
      deleteBtn.onclick = (e) => {
        e.preventDefault();
        if (confirm("{{ _('確定刪除?')}}")) {
          let wrapper = document.getElementById(`unit-${e.currentTarget.dataset.index}-wrapper`);
          unitContainer.removeChild(wrapper);
        }
      };
      let branchBtn = unitCard.querySelector('#card-branch-button');
      branchBtn.id = `unit-${index}-card-branch-button`;
      branchBtn.dataset.index = index;
      branchBtn.onclick = (e) => {
        e.preventDefault();
        createUnit({parent_id: unit.id});

      };

      let printBtn = unitCard.querySelector('#card-print-button');
      printBtn.id = `unit-${index}-card-print-button`;
      printBtn.dataset.index = index;
      printBtn.setAttribute('href', `/admin/print-label?entities=u${unit.id}`);

      let frontendLink = unitCard.querySelector('#card-frontend-link');
      if (unit.pub_status === 'P') {
        frontendLink.id = `unit-${index}-card-frontend-link`;
        frontendLink.dataset.index = index;
        frontendLink.setAttribute('href', `/collections/${unit.id}`);
      } else {
        frontendLink.remove();
      }

      let detailToggle = unitCard.querySelector('#card-detail-toggle');
      detailToggle.id = `unit-${index}-card-detail-toggle`;
      detailToggle.setAttribute('href', `#unit-${index}-modal`);

      // unitModal
      unitModal.id = `unit-${index}-modal`;
      unitModal.dataset.index = index;
      unitModal.classList.add('unit-box');

      let assertionContainer = unitModal.querySelector('#unit-assertion-container');
      assertionContainer.id = `unit-${index}-assertion-container`;
      let annotationContainer = unitModal.querySelector('#unit-annotation-container');
      annotationContainer.id = `unit-${index}-annotation-container`;

      let unitIdDisplay = unitModal.querySelector('#unit-id-display');
      unitIdDisplay.id = `unit-${index}-id-display`;
      unitIdDisplay.textContent = unit.id;

      // upload new image
      let uploadImageFile = unitModal.querySelector(`[data-unit="upload-image-file"]`);
      uploadImageFile.id = `unit-${index}-upload-image-id`;
      let uploadImageSubmit = unitModal.querySelector(`[data-unit="upload-image-submit"]`);
      uploadImageSubmit.id = `unit-${index}-upload-image-submit-id`;

      let uploadImageInput = unitModal.querySelector(`[data-unit="upload-image-input"]`);
      uploadImageInput.id = `unit-${index}-upload-image-input-id`; // 沒有用到(for UI display)
      if (!unit.id) {
        uploadImageInput.classList.add('uk-hidden');
        uploadImageSubmit.classList.add('uk-hidden');
      }
      uploadImageSubmit.onclick = (e) => {
        e.preventDefault();
          uploadImageSubmit.setAttribute('disabled', '');
          uploadImageSubmit.textContent = "{{ _('上傳中') }}...";
          if (uploadImageFile.files.length > 0) {
            let file = uploadImageFile.files[0];

            var formData = new FormData();
            formData.append('file', file);
            formData.append('unit_id', unit.id);

            fetch(`/admin/api/units/${unit.id}/media`, {
              method: 'POST',
              body: formData,
            })
              .then((response) => response.json())
              .then((json) => {
                //console.log(json);
                if (json.message === 'ok') {
                  UIkit.notification('上傳完成', {timeout: 1000});
                  const timeoutID = window.setTimeout(( () => {
                    location.reload();
                  }), 1200);
                }
              })
              .catch((error) => {
                console.error(error);
              });
          }
        };

      let unitMediaWrapper = unitModal.querySelector('#unit-media-wrapper');      unitMediaWrapper.id = `unit-${index}-media-wrapper`;
      if (unit.multimedia_objects && unit.multimedia_objects.length > 0) {
        unit.multimedia_objects.forEach( media => {
          let mediaItem = document.createElement('div');
          let mediaItemImg = document.createElement('img');
          mediaItemImg.src = media.file_url;
          mediaItemImg.setAttribute('width', '75');
          mediaItem.appendChild(mediaItemImg);

          let mediaItemCtrlArea = document.createElement('div');
          mediaItemCtrlArea.appendChild(document.createTextNode('[ '));

          let mediaItemDelete = document.createElement('a');
          mediaItemDelete.setAttribute('href', '#');
          mediaItemDelete.setAttribute('title', "{{ _('刪除') }}");
          mediaItemDelete.dataset.mediaid = media.id;
          mediaItemDelete.onclick = (e) => {
            e.preventDefault();
            if (confirm("{{ _('確定刪除照片?') }}")) {
              fetch(`/admin/api/units/${unit.id}/media/${e.target.dataset.mediaid}`, {
                method: 'DELETE',
              })
                .then(resp => resp.json())
                .then(json => {
                  if (json.message === 'ok') {
                    UIkit.notification('已刪除', {timeout: 500});
                    const timeoutID = window.setTimeout(( () => {
                      location.reload();
                    }), 800);
                  }
                });
            }
          };
          mediaItemDelete.textContent = "{{ _('刪除') }}";

          mediaItemCtrlArea.appendChild(mediaItemDelete);
          mediaItemCtrlArea.appendChild(document.createTextNode(' | '));

          let mediaItemSetCover = document.createElement('a');
          if (unit.cover_image && unit.cover_image.id === media.id) {
            mediaItemCtrlArea.appendChild(document.createTextNode(' -- '));
          } else {
            mediaItemSetCover.textContent = "{{ _('設定為封面') }}";
            mediaItemSetCover.setAttribute('href', '#');
            mediaItemSetCover.setAttribute('title', "{{ _('設定為封面') }}");
            mediaItemSetCover.dataset.mediaid = media.id;
            mediaItemSetCover.onclick = (e) => {
              e.preventDefault();
              fetch(`/admin/api/units/${unit.id}/media/${e.target.dataset.mediaid}?action=set-cover`, {
                method: 'POST',
              })
                .then(resp => resp.json())
                .then(json => {
                  //console.log(json);
                  if (json.message === 'ok') {
                    UIkit.notification('已設定', {timeout: 500});
                    const timeoutID = window.setTimeout(( () => {
                      location.reload();
                    }), 800);
                  }
              });
            };
            mediaItemCtrlArea.appendChild(mediaItemSetCover);
          }

          mediaItemCtrlArea.appendChild(document.createTextNode(' ]'));

          mediaItem.appendChild(mediaItemCtrlArea);
          unitMediaWrapper.appendChild(mediaItem);
        });
      } // end of multimedia_objecs

      ['id', 'guid'].forEach( field => {
        let elem = unitModal.querySelector(`[data-unit="${field}"]`);
        elem.id = `unit-${index}-${field}-id`;
        elem.value = unit[field] || '';
      });
      let selectFields = ['preparation_type', 'kind_of_unit', 'disposition', 'acquisition_type', 'type_status', 'basis_of_record'];
      allOptions._unit_fields.forEach( field => {
        if (field.indexOf(selectFields) < 0) {
          let elem = unitModal.querySelector(`[data-unit="${field}"]`);
          elem.id = `unit-${index}-${field}-id`;
          elem.value = unit[field] || '';
          elem.oninput = (e, key=field) => {
            if (unit[key] === e.target.value) {
              e.target.classList.remove('uk-form-success');
            } else {
              e.target.classList.add('uk-form-success');
            }
          };
        }
      });
      // select elements
      selectFields.forEach ( field => {
        let s = unitModal.querySelector(`#unit-${index}-${field}-id`);
        let options = allOptions[`unit_${field}`].map( x => ({id: x[0], text: x[1]}));
        makeOptions(s, options, unit[field] || '');
        s.onchange = (e, key=field) => {
          if (unit[key] === e.target.value) {
            e.target.classList.remove('uk-form-success');
          } else {
            e.target.classList.add('uk-form-success');
          }
        };
      });
      // select2
      ['tracking_tags__rfid'].forEach ( field => {
        let s = unitModal.querySelector(`[data-unit="${field}"]`);
        s.id = `unit-${index}-${field}-id`;
        let data = (unit.tracking_tags?.rfid) ? [{id: unit.tracking_tags.rfid.id, text: unit.tracking_tags.rfid.label}] : [];
        $(s).select2({
          width: '100%',
          dropdownParent: $(unitModal),
          ajax: {
            url: `/admin/api/collections/${unit.collection_id}/tracking-tags`,
            delay: 250,
            data: function (params) {
              if (params?.term?.length >= 1) {
                var query = {
                  filter: JSON.stringify({
                    q: params.term,
                    tag_type: 'rfid',
                  }),
                };
                return query;
              }
            },
            processResults: function (data) {
              console.log(data);
              return {
                results: data.map( x => ({id: x.id, text: x.label}))
              };
            }
          },
          data: data,
      });
      });

      unitContainer.appendChild(unitCard);
      document.getElementById('unit-modal-container').appendChild(unitModal);

      renderAttributes(assertionContainer.id, allOptions.assertion_type_unit_list, `unit-${index}-assertion`, unit.assertions, `unit-${index}-modal`);
      renderAttributes(annotationContainer.id, allOptions.annotation_type_unit_list, `unit-${index}-annotation`, unit.annotations, `unit-${index}-modal`);

    }; // end of createUnit

    initUnitValues.forEach( x => {
      createUnit(x);
    });

    document.getElementById('unit-add-button').onclick = () => {
      createUnit({});
    };
  };

  const init = () => {
    Promise.all(fetchUrls.map( url => {
      return fetch(url).then(resp => resp.json());
    }))
      .then( responses => {
        console.log('init', responses);
        resolveInit(responses);
      })
      .catch(error => {
        //console.error('Error init:', error)
        alert(error);
      });
  };

  const resolveInit = ([allOptions, values={}]) => {
    const collectors = allOptions.person_list
          .filter( x => x.is_collector )
          .map( x => ({ id: x.id, text: x.display_name }));
    const identifiers = allOptions.person_list
          .filter(x => x.is_identifier)
          .map( x => ({ id: x.id, text: x.display_name }));

    /*
    if (values.units[0] && values.units[0].image_url) {
      document.getElementById('image-url').src = values.units[0].image_url.replace('-s', '-m');
      document.getElementById('modal-image-url').src= values.units[0].image_url.replace('-s', '-o');
      }*/


    // init select2
    $('#collector-id').select2({data: collectors}).on('change', (e, v=(values?.collector) ? values.collector.id : '') => onSelect2Change(e.target, v));
    let recordGroupOptions = allOptions.record_groups.reduce((acc, item) => {
      if (!acc[item.category]) {
        acc[item.category] = {
          text: item.category,
          children: [],
        };
      }
      acc[item.category].children.push({
        text: item.text,
        id: item.id,
      });
      return acc;
    }, {});

    $('#record_groups-id')
      .select2({
        data: Object.values(recordGroupOptions),
        multiple: 'multiple',
      })
      .on('change', (e, v=(values?.groups) ? values.groups.map( x => x.id) : []) => onSelect2ChangeArr(e.target, v));

    // geo conv
    let geoElem = {
      xDir: document.getElementById('lon-dir-id'),
      xDeg: document.getElementById('lon-degree-id'),
      xMin: document.getElementById('lon-minute-id'),
      xSec: document.getElementById('lon-second-id'),
      xDec: document.getElementById('longitude_decimal-id'),
      yDir: document.getElementById('lat-dir-id'),
      yDeg: document.getElementById('lat-degree-id'),
      yMin: document.getElementById('lat-minute-id'),
      ySec: document.getElementById('lat-second-id'),
      yDec: document.getElementById('latitude_decimal-id'),
    };
    document.querySelectorAll('.ndb-conv-coordinate').forEach( input => {
      input.addEventListener('input', (e) => {
        let prefix = e.target.id.substring(0, 4);
        if (prefix === 'lon-') {
          let dir = geoElem.xDir.value;
          let d = geoElem.xDeg.value;
          let m = geoElem.xMin.value;
          let s = geoElem.xSec.value;
          let isValid = true;
          if (d >= 0 && d <= 180) {
            geoElem.xDeg.classList.remove('uk-form-danger');
          }
          else {
            geoElem.xDeg.classList.add('uk-form-danger');
            isValid = false;
          }
          if (m >= 0 && m <= 60) {
            geoElem.xMin.classList.remove('uk-form-danger');
          } else {
            geoElem.xMin.classList.add('uk-form-danger');
            isValid = false;
          }
          if (s >= 0 && s <= 60) {
            geoElem.xSec.classList.remove('uk-form-danger');
          } else {
            geoElem.xSec.classList.add('uk-form-danger');
            isValid = false;
          }
          if (isValid === true) {
            geoElem.xDec.value = convertDMSToDD([dir, d, m, s]);
          }
        } else if (prefix === 'lat-') {
          let dir = geoElem.yDir.value;
          let d = geoElem.yDeg.value;
          let m = geoElem.yMin.value;
          let s = geoElem.ySec.value;
          let isValid = true;
          if (d >= 0 && d <= 180) {
            geoElem.yDeg.classList.remove('uk-form-danger');
          }
          else {
            geoElem.yDeg.classList.add('uk-form-danger');
            isValid = false;
          }
          if (m >= 0 && m <= 60) {
            geoElem.yMin.classList.remove('uk-form-danger');
          } else {
            geoElem.yMin.classList.add('uk-form-danger');
            isValid = false;
          }
          if (s >= 0 && s <= 60) {
            geoElem.ySec.classList.remove('uk-form-danger');
          } else {
            geoElem.ySec.classList.add('uk-form-danger');
            isValid = false;
          }
          if (isValid === true) {
            geoElem.yDec.value = convertDMSToDD([dir, d, m, s]);
          }
        } else if (prefix === 'long') {
          let v = geoElem.xDec.value;
          if (v === values.longitude_decimal) {
            geoElem.xDec.classList.remove('uk-form-success');
          } else {
            geoElem.xDec.classList.add('uk-form-success');
          }
          let isValid = true;
          if (Math.abs(v) >= 0 && Math.abs(v) <= 180 ) {
            geoElem.xDec.classList.remove('uk-form-danger');
          } else {
            geoElem.xDec.classList.remove('uk-form-success');
            geoElem.xDec.classList.add('uk-form-danger');
            isValid = false;
          }
          if (isValid === true) {
            let dms = convertDDToDMS(v);
            geoElem.xDir.value = dms[0];
            geoElem.xDeg.value = dms[1];
            geoElem.xMin.value = dms[2];
            geoElem.xSec.value = dms[3];
            geoElem.xDec.classList.remove('uk-form-danger');
          } else {
            geoElem.xDec.classList.add('uk-form-danger');
          }
        } else if (prefix === 'lati') {
          let v = geoElem.yDec.value;
          if (v === values.latitude_decimal) {
            geoElem.yDec.classList.remove('uk-form-success');
          } else {
            geoElem.yDec.classList.add('uk-form-success');
          }
          let isValid = true;
          if (Math.abs(v) >= 0 && Math.abs(v) <= 90 ) {
            geoElem.yDec.classList.remove('uk-form-danger');
          } else {
            geoElem.yDec.classList.remove('uk-form-success');
            geoElem.yDec.classList.add('uk-form-danger');
            isValid = false;
          }
          if (isValid === true) {
            let dms = convertDDToDMS(v);
            geoElem.yDir.value = dms[0];
            geoElem.yDeg.value = dms[1];
            geoElem.yMin.value = dms[2];
            geoElem.ySec.value = dms[3];
            geoElem.yDec.classList.remove('uk-form-danger');
          } else {
            geoElem.yDec.classList.add('uk-form-danger');
          }
        }
      });
    });
    // set values
    if (recordId) {
      for (let field of allOptions._record_fields) {
        if (values[field]) {
          $(`#${field}-id`).val(values[field]);
        }
      }

      if (values.collector) {
        $('#collector-id').val(values.collector.id).trigger('change');
      } else {
        $('#collector-id').val('').trigger('change');
      }
      if (values.groups.length > 0) {
        $('#record_groups-id').val(values.groups.map( x => x.id)).trigger('change');
      } else {
        $('#record_groups-id').val([]);
      }
        // nav update
      document.getElementById('ndb-nav-identification-num').textContent = `(${values.identifications.length})`;

      // map
      if (values.latitude_decimal && values.longitude_decimal) {
        let map = L.map('record-map', {scrollWheelZoom: false}).setView([values.latitude_decimal, values.longitude_decimal], 10);
        const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19,
          attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(map);
        const marker = L.marker([values.latitude_decimal, values.longitude_decimal]).addTo(map);
      } else {
        document.getElementById('record-map-wrapper').classList.add('uk-hidden');
      }
    } else {
      $('#collector-id').val('').trigger('change');
    }
    initNamedAreas(values.named_areas || {}, allOptions.named_areas);
    renderAttributes('record-assertions', allOptions.assertion_type_record_list, 'record-assertion', values.assertions || {});
    initIdentifications(allOptions._identification_fields, identifiers, values.identifications || []);
    initUnits(allOptions, values.units || []);

    allOptions._record_fields.forEach( field => {
      //console.log(field);
      let elem = document.getElementById(`${field}-id`);

      elem.addEventListener('input', (e,  v=values[field]) => {
        if (v === e.target.value) {
          e.target.classList.remove('uk-form-success');
        } else {
          e.target.classList.add('uk-form-success');
        }
      });
    });
    document.getElementById('delete-button').onclick = async (e) => {
      e.preventDefault();
      if (confirm("{{ _('確定刪除? 包含標本/鑑定...都會一同刪除')}}")) {
        let result  = await deleteRecord();
        UIkit.notification('已刪除', {timeout: 1000});
        const timeoutID = window.setTimeout(( () => {
          location.replace('/admin/records');
        }), 1000);
      }
    };
    document.getElementById('save-test-button').onclick = (e) => {
      e.preventDefault();
      let payload = preparePayload(allOptions);
      console.log(payload);
    };
    document.getElementById('save-new-button').onclick = (e) => {
      e.preventDefault();
      UIkit.modal.prompt('這次改了什麼:', '').then(function (changelog) {
        if (changelog) {
          let payload = preparePayload(allOptions);
          payload.__changelog__ = changelog;
          saveRecord(payload, '/admin/records/create?collection_id={{ collection_id }}');
        }
      });
    };
    document.getElementById('save-cont-button').onclick = (e) => {
      e.preventDefault();
      e.target.blur();
      UIkit.modal.prompt('這次改了什麼:', '').then(function (changelog) {
        if (changelog) {
          let payload = preparePayload(allOptions);
          payload.__changelog__ = changelog;
          if (recordId) {
            saveRecord(payload, '.');
          } else {
            saveRecord(payload, 'result');
          }
        }
      });
    };
    document.getElementById('save-button').onclick = (e) => {
      e.preventDefault();
      UIkit.modal.prompt('這次改了什麼:', '').then(function (changelog) {
        if (changelog) {
          let payload = preparePayload(allOptions);
          payload.__changelog__ = changelog;
          saveRecord(payload, '/admin/records');
        }
      });
    };

    // render phase1
    if (allOptions._phase1) {
      const rawDataContainer = document.getElementById('raw-data-container');
      allOptions._phase1.form.forEach( x => {
        const wrapper = document.createElement('div');
        wrapper.classList.add('uk-width-1-1');
        const fieldset = document.createElement('fieldset');
        fieldset.classList.add('uk-fieldset');
        const legend = document.createElement('legend');
        legend.classList.add('uk-legend');
        legend.textContent = x[0];
        const grid = document.createElement('grid');
        grid.classList.add('uk-grid-small');
        grid.setAttribute('uk-grid', '');
        x[1].forEach( y => {
          y.forEach( z => {
            const widget = document.createElement('div');
            widget.classList.add(`uk-width-1-${y.length}`);
            const margin = document.createElement('div');
            margin.classList.add('uk-margin');
            const label = document.createElement('label');
            label.classList.add('uk-form-label');
            label.setAttribute('for', `raw-${z}-id`);
            //const fieldInfo = findItem(z, allOptions._phase1.fields, true);
            label.textContent = (allOptions._phase1.fields[z]) ? allOptions._phase1.fields[z][0] : '';
            const control = document.createElement('div');
            control.classList.add('uk-form-controls');

            if (allOptions._phase1.fields[z] && allOptions._phase1.fields[z].length === 1 ) {
              const input = document.createElement('input');
              input.classList.add('uk-input', 'uk-form-small', 'ndb-phase1-raw');
              input.id = `raw-${z}-id`;
              let val = values.raw_data[z] || '';
              input.value = val;
              input.setAttribute('name', `raw_${z}`);
              input.oninput = (e) => {
                if ( val === e.target.value) {
                  e.target.classList.remove('uk-form-success');
                } else {
                  e.target.classList.add('uk-form-success');
                }
              };
              control.appendChild(input);
            } else {
            }
            margin.appendChild(label);
            margin.appendChild(control);
            widget.appendChild(margin);
            grid.appendChild(widget);
          });
        });
        fieldset.appendChild(legend);
        fieldset.appendChild(grid);
        wrapper.appendChild(fieldset);
        rawDataContainer.appendChild(wrapper);
      });
    }
    // changelog
    const changelogContainer = document.getElementById('changelog-container');
    if ('__histories__' in values) {
      values.__histories__.forEach( item => {
        let changelog = document.getElementById('template-changelog').content.cloneNode(true);
        let changelogTitle = changelog.querySelector('#changelog-title');
        changelogTitle.textContent = `${item.created} | ${item.user.username} | ${item.action} | ${item.remarks || ''}`;
        let changelogContent = changelog.querySelector('#changelog-content');
        changelogContent.textContent = JSON.stringify(item.changes, null, 4);
        changelogContainer.appendChild(changelog);
      });
    }

    // source_data
    const sourceData = document.getElementById('sourcedata-content');
    sourceData.textContent = JSON.stringify(values.source_data, null, 4);

  }; // end of init

  init();
});

/*
 * basic javascript interactions
 */
(function() {
  'use strict';
  // hidden left-col button
  let hideBtn = document.getElementById('hide-left-col-btn');
  hideBtn.onclick = () => {
    let content = document.getElementById('content');
    let topHead = document.getElementById('top-head');
    let leftCol = document.getElementById('left-col');
    if (leftCol.classList.contains('uk-hidden') === false) {
      leftCol.classList.remove('uk-visible@m');
      leftCol.classList.add('uk-hidden');
      content.style.marginLeft = 0;
      topHead.style.left = '0px';
      hideBtn.innerHTML = `<span uk-icon="icon: chevron-double-left;"></span>{{ _('打開側邊欄') }}`;
    } else {
      leftCol.classList.remove('uk-hidden');
      leftCol.classList.add('uk-visible@m');
      content.style.marginLeft = '240px';
      topHead.style.left = '240px';
      hideBtn.innerHTML = `<span uk-icon="icon: chevron-double-left;"></span>{{ _('關閉側邊欄') }}`;
    }
  };

  // tabs
  let tabNavs = document.getElementsByClassName('ndb-tab-nav');
  let tabViews = document.getElementsByClassName('ndb-tab-view');
  for (let nav of tabNavs) {
    nav.onclick = (e) => {
      for (let view of tabViews) {
        if (nav.dataset.tab === view.dataset.tab) {
          view.classList.remove('uk-hidden');
        } else {
          view.classList.add('uk-hidden');
        }
      }
    };
  }
})();
