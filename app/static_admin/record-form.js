/* import {
 *   fetchData,
 *   getRandString,
 * } from './utils.js' */

(function() {
  "use strict";

  // utils
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

  const getRandString = (length) => {
    return Math.random().toString(16).slice(2, parseInt(length, 10)+2);
  }

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
  }

  const convertDMSToDD = (ddms) => {
    /* arguments: degree, minute, second
     */
    // console.log(ddms);
    return ddms[0] * (parseFloat(ddms[1]) + parseFloat(ddms[2]) / 60 + parseFloat(ddms[3]) / 3600);
  }

  const selectedNamedArea = {};
  const getHigherAreaClass = (id) => {
    const payload = {
      filter: JSON.stringify({
        id: [id],
      }),
    }
    const queryString = new URLSearchParams(payload).toString();
    fetchData(`/api/v1/named_areas?${queryString}`)
      .then( resp => {
        const parent = resp.data[0];
        let parentInput = document.getElementById(`named_areas__${parent.area_class.name}-input`);
        parentInput.setAttribute('value', parent.display_name);
        let parentHiddenValue = document.getElementById(`named_areas__${parent.area_class.name}__hidden_value`);
        if (parentHiddenValue) {
          parentHiddenValue.setAttribute('value', parent.id);
        }
        if (parent.parent_id) {
          getHigherAreaClass(parent.parent_id);
        }
      });
  }

  /**
     key: value
     'urlPrefix',
     'itemDisplay',
     'itemSelect',
     'appendQuery',
     'preFetch',
     'dropdownClass',
     'defaultValue', set to hidden value
   */
  const MyListbox = (() => {
    'use strict';

    const wrapper = function(inputId) { // 這邊不能用 arrow function?
      let pub = {};

      // store element
      let state = {
        input: null,
        dropdown: null,
        dropdownList: [],
      };
      // store values
      let conf = {
        inputId: inputId,
      };
      state.input = document.getElementById(inputId);
      const attrString = state.input.getAttribute('my-listbox');
      attrString.replace(/\s+/g, '').split(';').filter( x => x.length>0).forEach( x => {
        let [key, value] = x.split(':');
        conf[key] = value || '';
      });

      state.input.addEventListener('input',(e) => {
        if (conf.hasOwnProperty('preFetch')) {
          if (e.target.value) {
            //console.log(state.dropdownListAll);
            const results = conf.items.filter( x => (x.display_name.indexOf(e.target.value)>=0));
            renderList(results);
          } else {
            renderList(conf.items);
          }
        } else {
          if (e.target.value) {
            const filter = { q: e.target.value };
            if (conf.appendQuery) {
              for (const qPart of conf.appendQuery.split(',')) {
                const [k, v] = qPart.split('=');
                filter[k] = v
              }
            }
            if (inputId.indexOf('named_areas__') >=0 && conf.parentName) {
              const parentInputValue = document.getElementById(`named_areas__${conf.parentName}__hidden_value`);
              if (parentInputValue && parentInputValue.getAttribute('value')) {
                filter['parent_id'] = parentInputValue.getAttribute('value');
              }
            }
            const payload = {
              filter: JSON.stringify(filter),
            }
            //console.log(filter);
            const queryString = new URLSearchParams(payload).toString()
            const endpoint = `${conf.urlPrefix}?${queryString}`;
            // console.log(endpoint, filter);
            fetchData(endpoint)
              .then( resp => {
                renderList(resp.data);
              })
              .catch( error => {
                console.log(error);
              });
          } else {
            //UIkit.dropdown(`#${conf.dropdownId}`).hide(false);
            const inputValue = document.getElementById(`${state.input.name}__hidden_value`);
            inputValue.value = '';
          }
        }
      });
      const rand = getRandString(4);
      conf.dropdownId = `de-${conf.inputId}__dropdown-${rand}`;
      // create DOM
      state.dropdown = document.createElement('div');
      state.dropdown.className = (conf.hasOwnProperty('dropdownClass')) ? conf.dropdownClass.replace(/\s+/g, ' ') : 'uk-width-1-1 uk-margin-remove';
      state.dropdown.setAttribute('uk-dropdown', `mode: click; pos: bottom-justify; boundary: !.${conf.inputId}; auto-update: false`);
      state.dropdown.setAttribute('id', conf.dropdownId);
      state.dropdownList = document.createElement('ul');
      state.dropdownList.className = 'uk-list uk-list-divider uk-padding-remove-vertical'
      state.input.insertAdjacentElement('afterend', state.dropdown);
      state.dropdown.appendChild(state.dropdownList);
      // console.log(conf);
      state.inputHiddenValue = document.createElement('input');
      state.inputHiddenValue.setAttribute('name', `${state.input.name}__hidden_value`);
      state.inputHiddenValue.setAttribute('id', `${state.input.name}__hidden_value`);
      state.inputHiddenValue.setAttribute('type', `hidden`);
      state.inputHiddenValue.setAttribute('value', conf.defaultValue || '');
      state.dropdown.insertAdjacentElement('afterend', state.inputHiddenValue);

      if (conf.hasOwnProperty('preFetch')) {
        const filter = { };
        if (conf.appendQuery) {
          const [k, v] = conf.appendQuery.split('=');
          filter[k] = v;
        }
        const payload = {
          filter: JSON.stringify(filter),
          range: [0, 500], // HACK
        }
        const queryString = new URLSearchParams(payload).toString()
        const endpoint = `${conf.urlPrefix}?${queryString}`;
        fetchData(endpoint)
          .then( resp => {
            renderList(resp.data);
            conf.items = resp.data;
          })
          .catch( error => {
            console.log(error);
          });
      }
      // end init

      const renderList = data => {
        state.dropdownList.innerHTML = '';
        data.forEach( (d, index) => {
          let item = document.createElement('li');
           // handle item select
          item.onclick = (e) => {
            state.input.value = d[conf.itemDisplay];
            //console.log(e, d, inputId);
            // auto fill higher namedAreas
            if (inputId.indexOf('named_areas__') >=0 && d.parent_id ) {
              // selectedNamedArea[d.area_class.name] = d.area_class.id;
              getHigherAreaClass(d.parent_id);
            }
            state.inputHiddenValue.value = (conf.hasOwnProperty('itemSelect')) ? d[conf.itemSelect] : d.id;
            UIkit.dropdown(`#${conf.dropdownId}`).hide(false);
          }
          item.dataset.key = index;
          item.classList.add('uk-flex', 'uk-flex-between');
          item.innerHTML = `
            <div class="uk-padding-small uk-padding-remove-vertical">${d[conf.itemDisplay]}</div>
            <div class="uk-padding-small uk-padding-remove-vertical uk-text-muted"></div>`;
          state.dropdownList.appendChild(item);
        });
      }

      return pub;
    }
    return wrapper;
  })();

  let inputListboxes = document.querySelectorAll('input[my-listbox]');
  const allListbox = [];
  // console.log(inputListboxes);
  inputListboxes.forEach( elem => {
    allListbox.push(new MyListbox(elem.id));
  });


  const replaceNew = (elem, len) => {
    elem.id = elem.id.replace('__NEW__', `__NEW-${len}__`);
    elem.name = elem.name.replace('__NEW__', `__NEW-${len}__`);
  }

  // handle id create/remove
  const createIdButton = document.getElementById('create-identification');
  const identificationContainer = document.getElementById('identification-container');
  const tpl = document.getElementById('identification-template');

  let identificationCreated = 0;
  createIdButton.onclick = (e) => {
    e.preventDefault();
    identificationCreated++;
    let tmp = tpl.firstElementChild.cloneNode(true);

    let label = tmp.children[0].innerHTML =`NEW ${identificationCreated}`;
    let taxonInput = tmp.children[1].children[0].children[0].children[1].children[0].children[1];
    let sequenceInput = tmp.children[1].children[1].children[0].children[1].children[0];
    let identifierInput = tmp.children[1].children[2].children[0].children[1].children[0].children[1];
    let dateInput = tmp.children[1].children[3].children[0].children[1].children[0];
    let removeLink = tmp.children[2].children[0];

    tmp.id = tmp.id.replace('__NEW__', `__NEW-${identificationCreated}__`);
    removeLink.onclick = (e) => {
      tmp.remove();
    }
    replaceNew(taxonInput, identificationCreated);
    replaceNew(sequenceInput, identificationCreated);
    replaceNew(identifierInput, identificationCreated);
    replaceNew(dateInput, identificationCreated);
    identificationContainer.appendChild(tmp);
    allListbox.push(new MyListbox(taxonInput.id));
    allListbox.push(new MyListbox(identifierInput.id));
  }

  // handle unit create/remove
  const createUnitButton = document.getElementById('create-unit');
  const unitContainer = document.getElementById('unit-container');
  const unitTpl = document.getElementById('unit-template');

  let unitCreated = 0;
  createUnitButton.onclick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    unitCreated++;
    let tmp = unitTpl.firstElementChild.cloneNode(true);
    console.log(tmp.id);
    let label = tmp.children[0].innerHTML =`NEW ${unitCreated}`;
    let catalogNumber = tmp.children[1].children[1].children[0].children[1].children[0];
    let preparationDate= tmp.children[1].children[2].children[0].children[1].children[0];
    let assertions = tmp.children[1].children[4].children;
    let typeStatus = tmp.children[1].children[6].children[0].children[1].children[0];
    let typifiedName = tmp.children[1].children[7].children[0].children[1].children[0];
    //console.log(tmp.children[1]);
    //let type_reference = tmp.children[1].children[8].children[0].children[1].children[0];
    //let type_reference_link = tmp.children[1].children[9].children[0].children[1].children[0];
    let removeLink = tmp.children[2].children[0];
    removeLink.onclick = (e) => {
      tmp.remove();
    }
    replaceNew(catalogNumber, unitCreated);
    replaceNew(preparationDate, unitCreated);
    replaceNew(typeStatus, unitCreated);
    replaceNew(typifiedName, unitCreated);
    //replaceNew(type_reference, unitCreated);
    //replaceNew(type_reference_link, unitCreated);
    let unit_assertion_ids = [];
    for (const ass of assertions) {
      let item = ass.children[0].children[1];
      if (item.children[0].dataset.type === 'select') {
        replaceNew(item.children[0].children[1], unitCreated);
        unit_assertion_ids.push(item.children[0].children[1].id);
      } else {
        replaceNew(item.children[0], unitCreated);
      }
    };
    unitContainer.appendChild(tmp);
    for (let id_ of unit_assertion_ids) {
      allListbox.push(new MyListbox(id_));
    }
  }

  const deleteMacroItems = document.getElementsByClassName('record-macroitem-delete');
  //console.log(deleteMacroItems);
  for (let deleteBtn of deleteMacroItems) {
    deleteBtn.onclick = (e) => {
      e.preventDefault();
      let itemWrapper = document.getElementById(`${e.target.dataset.type}__${e.target.dataset.item_id}__wrapper`);
      itemWrapper.remove();
    }
  };

  // init
  const longitudeDecimal = document.getElementById('longitude-decimal')
  const converterLongitudeDirection = document.getElementById('converter-longitude-direction')
  const converterLongitudeDegree = document.getElementById('converter-longitude-degree')
  const converterLongitudeMinute = document.getElementById('converter-longitude-minute')
  const converterLongitudeSecond = document.getElementById('converter-longitude-second')
  const latitudeDecimal = document.getElementById('latitude-decimal')
  const converterLatitudeDirection = document.getElementById('converter-latitude-direction')
  const converterLatitudeDegree = document.getElementById('converter-latitude-degree')
  const converterLatitudeMinute = document.getElementById('converter-latitude-minute')
  const converterLatitudeSecond = document.getElementById('converter-latitude-second')

  const syncConverterLongitude = () => {
    let v = parseFloat(longitudeDecimal.value);
    //v = Math.abs(v);
    if ((v >= 0 && v <= 180) || (v < 0 && v >= -180) ) {
      longitudeDecimal.classList.remove('uk-form-danger')
      const dmsLongitude = convertDDToDMS(v)
      console.log(dmsLongitude);
      converterLongitudeDirection.value = dmsLongitude[0]
      converterLongitudeDegree.value = dmsLongitude[1]
      converterLongitudeMinute.value = dmsLongitude[2]
      converterLongitudeSecond.value = dmsLongitude[3]
    } else {
      longitudeDecimal.classList.add('uk-form-danger')
    }
  }
  const syncConverterLatitude = () => {
    const v = parseFloat(latitudeDecimal.value);
    if ((v >= 0 && v <= 90) || (v < 0 && v >= -90) ) {
      latitudeDecimal.classList.remove('uk-form-danger')
      const dmsLatitude = convertDDToDMS(latitudeDecimal.value)
      converterLatitudeDirection.value = dmsLatitude[0]
      converterLatitudeDegree.value = dmsLatitude[1]
      converterLatitudeMinute.value = dmsLatitude[2]
      converterLatitudeSecond.value = dmsLatitude[3]
    } else {
      latitudeDecimal.classList.add('uk-form-danger')
    }
  }

  const syncLongitudeDecimal = () => {
    const d = Math.abs(converterLongitudeDegree.value)
    const m = converterLongitudeMinute.value

    if (d >= 0 && d <= 180) {
      converterLongitudeDegree.classList.remove('uk-form-danger')
      if (m >= 0 && m <= 90) {
        const DMSList = [
          converterLongitudeDirection.value,
          converterLongitudeDegree.value,
          converterLongitudeMinute.value,
          converterLongitudeSecond.value,
        ]
        longitudeDecimal.value = convertDMSToDD(DMSList)
        converterLongitudeMinute.classList.remove('uk-form-danger')
      } else {
        converterLongitudeMinute.classList.add('uk-form-danger')
      }
    } else {
      converterLongitudeDegree.classList.add('uk-form-danger')
    }
  }
  const syncLatitudeDecimal = () => {
    const d = Math.abs(converterLatitudeDegree.value)
    const m = converterLatitudeMinute.value

    if (d >= 0 && d <= 180) {
      converterLatitudeDegree.classList.remove('uk-form-danger')
      if (m >= 0 && m <= 90) {
        const DMSList = [
          converterLatitudeDirection.value,
          converterLatitudeDegree.value,
          converterLatitudeMinute.value,
          converterLatitudeSecond.value,
        ]
        latitudeDecimal.value = convertDMSToDD(DMSList)
        converterLatitudeMinute.classList.remove('uk-form-danger')
      } else {
        converterLatitudeMinute.classList.add('uk-form-danger')
      }
    } else {
      converterLatitudeDegree.classList.add('uk-form-danger')
    }
  }

  syncConverterLongitude()
  syncConverterLatitude()

  longitudeDecimal.oninput = (e) => syncConverterLongitude()
  latitudeDecimal.oninput = (e) => syncConverterLatitude()
  converterLongitudeDirection.oninput = (e) => syncLongitudeDecimal()
  converterLongitudeDegree.oninput = (e) => syncLongitudeDecimal()
  converterLongitudeMinute.oninput = (e) => syncLongitudeDecimal()
  converterLongitudeSecond.oninput = (e) => syncLongitudeDecimal()
  converterLatitudeDirection.oninput = (e) => syncLatitudeDecimal()
  converterLatitudeDegree.oninput = (e) => syncLatitudeDecimal()
  converterLatitudeMinute.oninput = (e) => syncLatitudeDecimal()
  converterLatitudeSecond.oninput = (e) => syncLatitudeDecimal()  


  /***
  // form
  const recordForm = document.getElementById('record-form');
  recordForm.addEventListener('submit',  (event) => {
    event.preventDefault();
    console.log(event.submitter);
    const formData = new FormData(recordForm);

    formData.append("CustomField", "This is some extra data");

    fetch('http://127.0.0.1:5000/admin/api/records/135078', {
      method: 'POST',
      body: JSON.stringify(Object.fromEntries(formData)),
      headers: {
	'Content-type': 'application/json; charset=UTF-8'
      }
    }).then(function (response) {
      if (response.ok) {
	return response.json();
      }
      return Promise.reject(response);
    }).then(function (data) {
      console.log(data);
    }).catch(function (error) {
      console.warn(error);
    });
  });
  */
})();
