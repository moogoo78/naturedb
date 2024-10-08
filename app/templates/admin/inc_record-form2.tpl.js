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
};

const findItem = (key, options) => {
  let item = options.find( x => x[0] === key);
  if (item) {
    return item[1];
  } else {
    return '';
  }
};

const onSelect2 = (elem, initVal) => {
  if (parseInt(elem.value) === parseInt(initVal)) {
    $(elem).siblings('.select2').children('.selection').children('.select2-selection').css('border-color', '');
    $(elem).siblings('.select2').children('.selection').children('.select2-selection').children('.select2-selection__rendered').css('color', '');
  } else {
    $(elem).siblings('.select2').children('.selection').children('.select2-selection').css('border-color', '#32d296');
    $(elem).siblings('.select2').children('.selection').children('.select2-selection').children('.select2-selection__rendered').css('color', '#32d296');
  }
};

/*
 * jquery ready
 */
$( document ).ready(function() {
  const fetchUrls = [
    '/admin/api/collections/{{ collection_id }}/records/{{ record_id}}',
    '/admin/api/collections/{{ collection_id }}/options',
  ];

  const fetchNamedAreaOptions = async (area_class_id, parent_id) => {
    const filtr = {
      parent_id: parent_id,
      area_class_id: area_class_id,
    };
    const url = `/api/v1/named-areas?filter=${JSON.stringify(filtr)}`;
    const res = await fetchData(url);
    return res.data.map( x => ({ id: x.id, text: x.display_name }));
  };

  const renderAttributes = (container, options, prefix, isUnit=false) => {
    for (let item of options) {
      let assertion = document.getElementById('template-widget').content.cloneNode(true);
      let label = assertion.querySelector('label');
      label.textContent =  item.label;
      label.setAttribute('for', item.name);
      let itemId = `${prefix}-${item.name}-id`;
      let itemElement = null;
      if (item.input_type === 'free') {
        itemElement = document.getElementById('template-widget-select2').content.cloneNode(true);
        let s = itemElement.querySelector('select');
        s.id = itemId;
        s.dataset.tags = true;
        let counter = 0;
        for (let x of item.options) {
          counter += 1;
          s[counter] = new Option(x.display_name, x.id, false, false);
        }
      } else if (item.input_type === 'select') {
        itemElement = document.createElement('select');
        itemElement.classList.add('uk-select');
        itemElement.id = itemId;
        let counter = 0;
        for (let x of item.options) {
          counter += 1;
          itemElement[counter] = new Option(x[1], x[0], false, false);
        }
      } else if (item.input_type === 'input') {
        itemElement = document.createElement('input');
        itemElement.classList.add('uk-input');
        itemElement.id = itemId;
      } else if(item.input_type === 'text') {
        itemElement = document.createElement('textarea');
        itemElement.classList.add('uk-textarea');
        itemElement.id = itemId;
      } else if (item.input_type === 'checkbox') {
        itemElement = document.createElement('input');
        itemElement.classList.add('uk-checkbox');
        itemElement.setAttribute('type', 'checkbox');
        itemElement.id = itemId;
      }
      assertion.querySelector('.uk-form-controls').appendChild(itemElement);
      container.appendChild(assertion);
      if (item.input_type === 'free') {
        if (isUnit === true) {
          $(`#${itemId}`).select2({
            dropdownParent: $('#modal-unit-detail'),
            width: '100%',
          });
        } else {
          $(`#${itemId}`).select2({width: '100%'});
        }
      }
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
      //$(`#${widgetId}`).select2({data: options}).on('change', (e, v=val) => onSelect2(e, v));

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
        onSelect2(e.target, named_areas.COUNTRY.id);
      }
    });
    $('#ADM1-id').on('change', async (e) => {
      $('#ADM2-id').empty();
      $('#ADM3-id').empty();
      if (e.target.value) {
        const options = await fetchNamedAreaOptions(9, e.target.value);
        $('#ADM2-id').select2({data: options}).val('').select2();
        onSelect2(e.target, named_areas.ADM1.id);
      }
    });
    $('#ADM2-id').on('change', async (e) => {
      $('#ADM3-id').empty();
      if (e.target.value) {
        const options = await fetchNamedAreaOptions(10, e.target.value);
        $('#ADM3-id').select2({data: options}).val('').select2();
        onSelect2(e.target, named_areas.ADM2.id);
      }
    });

    $('#ADM3-id').on('change', (e) => {
      onSelect2(e.target, named_areas.ADM3.id);
    });

  };

  const initIdentifications = (data, identifiers) => {
    let idContainer = document.getElementById('identification-container');

    let identificationNum = 0;
    const createIdentificationCard = (values) => {
      identificationNum += 1;
      let index = identificationNum;
      let idCard = document.getElementById('template-identification').content.cloneNode(true);
      console.log(index, values);
      idCard.children[0].setAttribute('id', `identification-${index}-wrapper`);
      idCard.querySelector('.uk-label-success').textContent = index;
      // set element id
      const idFields = ['taxon', 'identifier', 'date', 'date_text', 'verbatim_identification', 'verbatim_identifier', 'verbatim_date', 'note', 'delete-button'];
      idFields.forEach( field => {
        let elem = idCard.querySelector(`#${field}-id`);
        elem.setAttribute('id', `identification-${index}-${field}-id`);
        if (field === 'identifier') {
          $(elem).select2({
            data: identifiers,
            width: '100%',
          });
        } else if (field === 'taxon') {
          $(elem).select2({
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
            }
          });
        }
      });
      let deleteButton = idCard.querySelector(`#identification-${index}-delete-button-id`);
      deleteButton.dataset.index = index;
      deleteButton.onclick = (e) => {
        if (confirm("{{ _('確定刪除?')}}")) {
          let elem = document.getElementById(`identification-${e.target.dataset.index}-wrapper`);
          idContainer.removeChild(elem);
        }
      };
      idContainer.appendChild(idCard);
    };

    document.getElementById('identification-add-button').onclick = () => {
      createIdentificationCard();
    };
    for (let i of data) {
      createIdentificationCard(i);
    }

    if (data[0].taxon) {
      let lastId = document.getElementById('last_identification-id');
      if (data[0].identifier) {
        lastId.setAttribute('value', `${data[0].taxon.display_name} | ${data[0].identifier.display_name}`);
      } else {
        lastId.textContent = `${data[0].taxon.display_name}`;
      }
    }
  };

  const initUnits = (units, allOptions, unitsEdited) => {
    let unitNum = 0;
    const tbody = document.querySelector('#unit-tbody');

    const openUnitModal = (unitIndex => {
      console.log(unitIndex);
      let unitValues = units[parseInt(unitIndex)-1];
      let mod = document.getElementById('modal-unit-detail');

      const onUnitInput = (e, v) => {
        console.log(e.target.value, v);
      };
      // set new indexed id
      // input elements
      ['guid'].forEach( field => {
        let elem = mod.querySelector(`[data-unit="${field}"]`);
        elem.id = `unit-${unitIndex}-${field}-id`;
        elem.value = unitValues[field];
      });
      ['accession_number', 'duplication_number', 'preparation_type', 'preparation_date', 'type_status', 'typified_name', 'type_is_published', 'type_reference', 'type_reference_link', 'type_note', 'kind_of_unit', 'disposition', 'pub_status', 'acquisition_type', 'acquisition_source_text'].forEach( field => {
        let elem = mod.querySelector(`[data-unit="${field}"]`);
        elem.id = `unit-${unitIndex}-${field}-id`;
        elem.value = unitValues[field];
        elem.oninput = (e, key=field, idx=unitIndex) => {
          if (unitValues[key] === e.target.value) {
            e.target.classList.remove('uk-form-success');
          } else {
            e.target.classList.add('uk-form-success');
            unitsEdited[idx-1][key] = e.target.value;
          }
        };
      });
      // select elements
      ['preparation_type', 'kind_of_unit', 'disposition', 'acquisition_type', 'type_status'].forEach ( field => {
        let s = mod.querySelector(`#unit-${unitIndex}-${field}-id`);
        s[0] = new Option("{{ _('-- 選澤 --') }}", '', false, false);
        allOptions[`unit_${field}`].forEach( (v, i) => {
          if (unitsEdited[unitIndex-1][field] && unitsEdited[unitIndex-1][field] === v[0]){
            s[i+1] = new Option(v[1], v[0], true, true);
          } else {
            s[i+1] = new Option(v[1], v[0], false, false);
          }
        });

        s.onchange = (e, key=field, idx=unitIndex) => {
          if (unitValues[key] === e.target.value) {
            e.target.classList.remove('uk-form-success');
          } else {
            e.target.classList.add('uk-form-success');
            unitsEdited[idx-1][key] = e.target.value;
          }
        };
      });

      // unit attribute (assertions & annotations)
      let container1 = document.getElementById('unit-assertion-container');
      container1.innerHTML = '';
      renderAttributes(container1, allOptions.assertion_type_unit_list, `unit-${unitIndex}-assertion`, true);
      let container2 = document.getElementById('unit-annotation-container');
      container2.innerHTML = '';
      renderAttributes(container2, allOptions.annotation_type_unit_list, `unit-${unitIndex}-annotation`, true);
    }); // end of openUnitModal


    const createUnitRow = (unit) => {
      unitNum += 1;
      let index = unitNum;
      const clone = document.getElementById('template-unit').content.cloneNode(true);
      clone.querySelector('tr').id = `unit-${index}-wrapper`;
      clone.querySelector('tr').dataset.index = index;
      let td = clone.querySelectorAll('td');
      td[0].querySelector('img').setAttribute('src', unit.image_url);
      const toggle = td[0].querySelector('a');
      toggle.dataset.img = unit.image_url;
      toggle.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        let bigimg = e.currentTarget.dataset.img.replace('-s', '-o');
        document.querySelector('#modal-specimen-image').querySelector('img').setAttribute('src', bigimg);
      };
      td[1].querySelector('a').setAttribute('href', `/specimens/${allOptions.collection.name.toUpperCase()}:${unit.accession_number}`);
      td[1].querySelector('a').textContent = unit.accession_number;
      td[2].textContent = findItem(unit.kind_of_unit, allOptions.unit_kind_of_unit);
      td[3].textContent = findItem(unit.preparation_type, allOptions.unit_preparation_type);
      td[4].textContent = findItem(unit.pub_status, allOptions.unit_pub_status);
      td[5].querySelector('a').dataset.index = index;
      td[5].querySelector('a').onclick = (e) => {
        e.preventDefault();
        openUnitModal(e.target.dataset.index);
      };
      td[6].querySelector('button').dataset.index = index;
      td[6].querySelector('button').onclick = (e) => {
        e.preventDefault();
        if (confirm("{{ _('確定刪除?')}}")) {
          unitNum -= 1;
          let wrapper = document.getElementById(`unit-${e.target.dataset.index}-wrapper`);
          tbody.removeChild(wrapper);
        }
      };

      tbody.appendChild(clone);
    };

    for (let unit of units) {
      createUnitRow(unit);
    }

    document.getElementById('unit-add-button').onclick = () => {
      createUnitRow({});
    };
  };

  const init = ([values, allOptions]) => {
    let relatedValues = {
      identifications: [...values.identifications],
      units: [...values.units],
      assertions: {...values.assertions},
    };
    let collectors = [];
    let identifiers = [];
    for (let person of allOptions.person_list) {
      if (person.is_collector) {
        collectors.push({
          id: person.id,
          text: person.display_name,
        });
      } else if (person.is_identifier) {
        identifiers.push({
          id: person.id,
          text: person.display_name,
        });
      }
    }

    /*
    if (values.units[0] && values.units[0].image_url) {
      document.getElementById('image-url').src = values.units[0].image_url.replace('-s', '-m');
      document.getElementById('modal-image-url').src= values.units[0].image_url.replace('-s', '-o');
      }*/


    // init select2
    $('#collector-id').select2({data: collectors}).on('change', (e, v=values.collector.id) => onSelect2(e.target, v));

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
    for (let field of values['__editable_fields__']) {
      if (values[field]) {
        $(`#${field}-id`).val(values[field]);
      }
    }
    if (values.collector) {
      $('#collector-id').val(values.collector.id).trigger('change');
    }
    initNamedAreas(values.named_areas, allOptions.named_areas);
    let container = document.getElementById('record-assertions');
    renderAttributes(container, allOptions.assertion_type_record_list, 'record-assertion');
    initIdentifications(values.identifications, identifiers);
    initUnits(values.units, allOptions, relatedValues.units);

    // nav
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

    values.__editable_fields__.forEach( field => {
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
    document.getElementById('delete-button').onclick = (e) => {
      e.preventDefault();
      let postData = {};
      values.__editable_fields__.forEach( field => {
        let elem = document.getElementById(`${field}-id`);
        postData[field] = elem.value;
      });
      console.log('post', postData);
      console.log(relatedValues);
    };
    document.getElementById('save-cont-button').onclick = (e) => {
      e.preventDefault();
      let postData = {};
      values.__editable_fields__.forEach( field => {
        let elem = document.getElementById(`${field}-id`);
        postData[field] = elem.value;
      });
      console.log('post', postData);
      console.log(relatedValues);
    };
    document.getElementById('save-button').onclick = (e) => {
      e.preventDefault();
      let postData = {};
      values.__editable_fields__.forEach( field => {
        let elem = document.getElementById(`${field}-id`);
        postData[field] = elem.value;
      });
      console.log('post', postData);
      console.log(relatedValues);
    };
  }; // end of init

  Promise.all(fetchUrls.map( url => {
    return fetch(url).then(resp => resp.json());
  }))
    .then( responses => {
      console.log('init', responses);
      init(responses);
    })
    .catch(error => console.error('Error fetching data:', error));
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
