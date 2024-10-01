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
/*
 * jquery ready
 */
$( document ).ready(function() {
  const fetchUrls = [
    '/admin/api/collections/{{ collection_id }}/records/{{ record_id}}',
    '/admin/api/collections/{{ collection_id }}/options',
  ];

  let state = {
    identificationNum: 0,
    unitNum: 0,
  };

  const fetchNamedAreaOptions = async (area_class_id, parent_id) => {
    const filtr = {
      parent_id: parent_id,
      area_class_id: area_class_id,
    };
    const url = `/api/v1/named-areas?filter=${JSON.stringify(filtr)}`;
    const res = await fetchData(url);
    return res.data.map( x => ({ id: x.id, text: x.display_name }));
  }

  const initNamedAreas = async (named_areas) => {
    if (named_areas.COUNTRY) {
      $('#COUNTRY-id').val(named_areas.COUNTRY.id).select2();
      const options = await fetchNamedAreaOptions(8, named_areas.COUNTRY.id);
      $('#ADM1-id').html('').select2({data: options}).val('');
    }
    if (named_areas.ADM1) {
      $('#ADM1-id').val(named_areas.ADM1.id).select2();
      const options = await fetchNamedAreaOptions(9, named_areas.ADM1.id);
      $('#ADM2-id').html('').select2({data: options}).val('').select2();
    }
    if (named_areas.ADM2) {
      $('#ADM2-id').val(named_areas.ADM2.id).select2();
      const options = await fetchNamedAreaOptions(10, named_areas.ADM2.id);
      $('#ADM3-id').html('').select2({data: options}).val('').select2();
    }
    if (named_areas.ADM3) {
      $('#ADM3-id').val(named_areas.ADM3.id).select2();
    }
  };

  $('#COUNTRY-id').on('change', async (e) => {
    $('#ADM1-id').empty();
    $('#ADM2-id').empty();
    $('#ADM3-id').empty();
    if (e.target.value) {
      const options = await fetchNamedAreaOptions(8, e.target.value);
      $('#ADM1-id').select2({data: options}).val('').select2();
      }
  });
  $('#ADM1-id').on('change', async (e) => {
    $('#ADM2-id').empty();
    $('#ADM3-id').empty();
    if (e.target.value) {
      const options = await fetchNamedAreaOptions(9, e.target.value);
      $('#ADM2-id').select2({data: options}).val('').select2();
    }
  });
  $('#ADM2-id').on('change', async (e) => {
    $('#ADM3-id').empty();
    if (e.target.value) {
      const options = await fetchNamedAreaOptions(10, e.target.value);
      $('#ADM3-id').select2({data: options}).val('').select2();
    }
  });

  const initAssertions = (typeList) => {
    let container = document.getElementById('record-assertions');
    let select2TagIds = [];
    for (let item of typeList) {
      //console.log(item);
      let assertion = document.getElementById('assertion-template').content.cloneNode(true);
      let label = assertion.querySelector('label');
      label.textContent =  item.label;
      label.setAttribute('for', item.name);
      if (item.input_type === 'free') {
        let select2Wrapper = document.getElementById('assertion-template-select2-tag').content.cloneNode(true);
        let s = select2Wrapper.querySelector('select');
        s.setAttribute('id', `record-assertion-${item.name}-id`);
        select2TagIds.push(s.id);
        for (let x of item.options) {
          s[x.id] = new Option(x.display_name, s.options.length, false, false);
        }
        assertion.querySelector('.uk-form-controls').appendChild(select2Wrapper);
       }
      container.appendChild(assertion);
    }

    for (let id of select2TagIds) {
      $(`#${id}`).select2();
    }
  };

  const initIdentifications = (data, identifiers) => {
    let idContainer = document.getElementById('identification-container');

    const createIdentificationCard = (values) => {
      state.identificationNum += 1;
      let index = state.identificationNum;
      let idCard = document.getElementById('identification-template').content.cloneNode(true);
      console.log(index, values);
      idCard.children[0].setAttribute('id', `identification-${index}-wrapper`);
      idCard.querySelector('.uk-label-success').textContent = index;
      // set element id
      const idFields = ['taxon', 'identifier', 'date', 'date_text', 'verbatim_identification', 'verbatim_identifier', 'verbatim_date', 'note', 'delete-button'];
      idFields.forEach( field => {
        let elem = idCard.querySelector(`#${field}-id`);
        elem.setAttribute('id', `identification-${index}-${field}-id`);
        if (field === 'identifier') {
          $(elem).select2({data: identifiers});
        } else if (field === 'taxon') {
          $(elem).select2({
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

  const initUnits = (units, allOptions) => {
    let unitContainer = document.getElementById('unit-container');
    const createUnitCard = (unit) => {
      state.unitNum += 1;
      let index = state.unitNum;
      let unitCard = document.getElementById('unit-template').content.cloneNode(true);
      unitCard.children[0].setAttribute('id', `unit-${index}-wrapper`);
      console.log(unitCard);
      console.log(index, unit);
      if (unit.image_url) {
        unitCard.querySelector('.unit-image').setAttribute('src', unit.image_url);
        }
      unitCard.querySelector('.unit-title').textContent = `${unit.accession_number}`; //${allOptions.collection.label}:
      unitCard.querySelector('.unit-meta').textContent = findItem(unit.kind_of_unit, allOptions.unit_kind_of_unit);
      unitCard.querySelector('.unit-pub-status').textContent = findItem(unit.pub_status, allOptions.unit_pub_status);
      //unitCard.querySelector('.unit-disposition').textContent = unit.disposition;
      unitCard.querySelector('.unit-delete').dataset.index = index;
      unitCard.querySelector('.unit-delete').onclick = (e) => {
        e.preventDefault();
        if (confirm("{{ _('確定刪除?')}}")) {
          let elem = document.getElementById(`unit-${e.target.dataset.index}-wrapper`);
          unitContainer.removeChild(elem);
        }
      };

      unitCard.querySelector('.unit-modal-open').dataset.index = index;
      unitCard.querySelector('.unit-modal-open').onclick = (e) => {
        let idx = e.target.dataset.index;
        let unitValues = units[parseInt(idx)-1];
        let mod = document.getElementById('modal-unit-detail');

        // set new indexed id
        ['accession_number', 'duplication_number', 'guid', 'preparation_type', 'preparation_date', 'type_status', 'typified_name', 'type_is_published', 'type_reference', 'type_reference_link', 'type_note', 'kind_of_unit', 'disposition', 'pub_status', 'acquisition_type', 'acquired_source_text'].forEach( field => {
          mod.querySelector(`#${field}-id`).setAttribute('id', `unit-${idx}-${field}-id`);
        });

        let s = mod.querySelector(`#unit-${idx}-preparation_type-id`);
        s[0] = new Option("{{ _('-- 選澤 --') }}", '', false, false);
        allOptions.unit_preparation_type.forEach( (v, i) => {
          s[i+1] = new Option(v[1], v[0], false, false);
        });
        s = mod.querySelector(`#unit-${idx}-kind_of_unit-id`);
        s[0] = new Option("{{ _('-- 選澤 --') }}", '', false, false);
        allOptions.unit_kind_of_unit.forEach( (v, i) => {
          s[i+1] = new Option(v[1], v[0], false, false);
        });
        s = mod.querySelector(`#unit-${idx}-disposition-id`);
        s[0] = new Option("{{ _('-- 選澤 --') }}", '', false, false);
        allOptions.unit_disposition.forEach( (v, i) => {
          s[i+1] = new Option(v[1], v[0], false, false);
        });
        s = mod.querySelector(`#unit-${idx}-acquisition_type-id`);
        s[0] = new Option("{{ _('-- 選澤 --') }}", '', false, false);
        allOptions.unit_acquisition_type.forEach( (v, i) => {
          s[i+1] = new Option(v[1], v[0], false, false);
        });
        s = mod.querySelector(`#unit-${idx}-type_status-id`);
        s[0] = new Option("{{ _('-- 選澤 --') }}", '', false, false);
        allOptions.unit_type_status.forEach( (v, i) => {
          s[i+1] = new Option(v[1], v[0], false, false);
        });
      };
      unitContainer.appendChild(unitCard);
    };
    for (let unit of units) {
      createUnitCard(unit);
    }

    document.getElementById('unit-add-button').onclick = () => {
      createUnitCard({});
    };
  };
  const init = ([values, allOptions]) => {

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
    const countries = allOptions.named_areas.country.options.map( x => {
      return {
        id: x.id,
        text: x.display_name,
      };
    });


    /*
    if (values.units[0] && values.units[0].image_url) {
      document.getElementById('image-url').src = values.units[0].image_url.replace('-s', '-m');
      document.getElementById('modal-image-url').src= values.units[0].image_url.replace('-s', '-o');
    }*/

    // init select2
    $('#collector-id').select2({data: collectors});
    $('#COUNTRY-id').select2({data: countries});
    $('#ADM1-id').select2();
    $('#ADM2-id').select2();
    $('#ADM3-id').select2();

    $('.ndb-conv-coordinate').on('input', (e) => {
      console.log(e.target.value, e.target.dataset.coordinate);
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
    initNamedAreas(values.named_areas);
    initAssertions(allOptions.assertion_type_record_list);
    initIdentifications(values.identifications, identifiers);
    initUnits(values.units, allOptions);
  }; // end of init

  Promise.all(fetchUrls.map( url => {
    return fetch(url).then(resp => resp.json());
  }))
    .then( responses => {
      console.log(responses);
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
