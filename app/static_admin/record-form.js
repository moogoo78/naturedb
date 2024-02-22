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
  const MyValidate = (() => {
    'use strict';

    const wrapper = function(inputId) {
      console.log(inputId)
      let pub = {
        input: null,
        inputId: inputId,
        helperText: null,
        conf: {},
      }
      pub.input = document.getElementById(inputId)
      const attrString = pub.input.getAttribute('my-validate')
      attrString.split(';').filter( x => x.length>0).forEach( x => {
        let [key, value] = x.split(':')
        let k = key.trim()
        pub['conf'][key.trim()] = (value && value.trim()) ||  ''
      })

      pub.input.addEventListener('input',(e) => {
        let endpoint = ''
        if (pub['conf'].hasOwnProperty('type')) {
          if (pub['conf']['type'] === 'exist') {
            endpoint = `/api/v1/validate/${pub.conf.resource}?exist=1&property=${pub.conf.property}&value=${e.target.value}`
            const helperTextId = `${pub.inputId}-helperText`;
            const help = document.getElementById(helperTextId)
            fetchData(endpoint)
              .then( resp => {
                console.log(resp.validate)
                if (resp.validate !== 'success') {
                  pub.input.classList.add('uk-form-danger')
                  if (help === null) {
                    pub.helperText = document.createElement('span')
                    pub.helperText.setAttribute('id', helperTextId)
                    pub.helperText.classList.add('uk-text-danger')
                    pub.helperText.innerHTML = '此館號已經輸入過了'
                    pub.input.insertAdjacentElement('afterend', pub.helperText)
                  }
                } else {
                  pub.input.classList.remove('uk-form-danger')
                  help.remove()
                }
              })
              .catch( error => {
                console.log(error)
              })
          }
        }
      })
      return pub
    }
    return wrapper
  })();

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
      //attrString.replace(/\s+/g, '').split(';').filter( x => x.length>0).forEach( x => {
      attrString.split(';').filter( x => x.length>0).forEach( x => {
        let [key, value] = x.split(':');
        let k = key.trim();
        conf[key.trim()] = (value && value.trim()) ||  '';
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

  const Helpers = (() => {
    const makeFetchUrl = (conf, appendQuery) => {
      const queryList = [];
      if ('query' in conf) {
        const filterParams = new URLSearchParams(conf.query);
        let params = Object.fromEntries(filterParams);
        if (appendQuery) {
          const pair = appendQuery.split('=');
          params = {
            ...params,
            [pair[0]]: pair[1],
          };
        }
        queryList.push(`filter=${JSON.stringify(params)}`);
      }
      if ('sort' in conf) {
        const sort = conf.sort.split(',').map(v => {
          return (v[0] === '-') ? {[v.substr(1)]:'desc'} : {[v]:''};
        });
        queryList.push(`sort=${JSON.stringify(sort)}`);
      }
      if ('range' in conf) {
        const range = JSON.parse(conf.range);
        queryList.push(`range=${JSON.stringify(range)}`);
      }
      let url = `${conf.fetch}`;
      if (queryList.length) {
        url = `${url}?${queryList.join('&')}`;
      }
      return url;
    };
    const renderOptions = (elementId, options, value, text, selectedId) => {
      let element = document.getElementById(elementId);
      if (selectedId === undefined) {
        element[0] = new Option('-- choose --', '', true, true);
        options.forEach( (v, i) => {
          element[i+1] = new Option(v[text], v[value], false);
        });
      } else {
        options.forEach( (v, i) => {
          if (String(v[value]) === String(selectedId)) {
            element[i+1] = new Option(v[text], v[value], true, true);
          }
          else {
            element[i+1] = new Option(v[text], v[value], false);
          }
        });
      }
    };

    const applyAdjacencyList = (elements, data, higherKey, optionMapKey, key) => {
      let depth = -1; // depth after current hiararchy (category)
      let currentIndex = -1;
      let higher = data[higherKey];
      let optionMap = data[optionMapKey];
      console.log(elements, data, higher, optionMap, key);
      let x = elements.splice(1, higher.length+2);
      console.log('xxxx', x);
      for (let i=0; i<x.length; i++) {
        console.log(elements[i]);
        //const entity = schema[key].entities[i][1];
        //const cat = entity.args.query.split('=')[1];
        //const isCurrentLayer = (String(cat) === String(result[relation.categoryName])) ? true : false;
      //  if (depth >= 0) {
      //    depth++;
       // }
        //if (isCurrentLayer === true) {
        //  depth = 0;
        //  currentIndex = i;
        //}
      }
    };
    return { makeFetchUrl, renderOptions, applyAdjacencyList};
  })();

  const Gazetter = (() => {
    let adjacencyList = [];
    let schema = {};

    const register = (formId) => {
      let form = document.getElementById(formId);
      for (const i in form.elements) {
        const input = form.elements[i];
        if (input.nodeName
            && input.hasAttribute('my-gazetter')
            && ['INPUT', 'SELECT'].indexOf(input.nodeName) >= 0) {
          let conf = {};
          const attrs = input.getAttribute('my-gazetter');
          attrs.split(';').filter( x => x.length>0).forEach( x => {
            let [key, value] = x.split(':');
            let k = key.trim();
            conf[key.trim()] = (value && value.trim()) ||  '';
          });
          let element = document.getElementById(input.id);
          if (conf.hasOwnProperty('intensive')) {
            adjacencyList.push([parseInt(conf.intensive), element]);
          }
          let data = {
            element: input,
            config: conf
          };
          schema[input.name] = data;
        }
        adjacencyList = adjacencyList.sort((a, b) => a[0] - b[0]);
        //console.log(adjacencyList);
      }
    }; // end of register

    const init = () => {
      for (let key in schema) {
        //console.log(key, schema[key]);
        const conf = schema[key].config;
        const input = schema[key].element;
        let url = Helpers.makeFetchUrl(conf);
          if ('preFetch' in conf) {
            fetchData(url)
              .then( resp => {
                let displayKey = conf.itemDisplay || 'display_name';
                Helpers.renderOptions(input.id, resp.data, 'id', displayKey);
              })
              .catch( error => {
                console.error(error);
              });
          }
          input.addEventListener("change", (event) => {
            let url2 = `${conf.fetch}/${event.target.value}?options=1`;
            fetchData(url2)
              .then( resp => {
                Helpers.applyAdjacencyList(
                  adjacencyList,
                  resp,
                  conf.higherClassificationName,
                  conf.optionMapName,
                  conf.keyName);
              })
              .catch( error => {
                console.error(error);
              });
          });
      }
    };// end of init

    return { register, init };
  })();

  let inputValidates = document.querySelectorAll('input[my-validate]');
  const allValidate = []
  inputValidates.forEach ( elem => {
    allValidate.push(new MyValidate(elem.id))
  })
  //console.log(inputValidates)

  let inputListboxes = document.querySelectorAll('input[my-listbox]');
  const allListbox = [];
  // console.log(inputListboxes);
  inputListboxes.forEach( elem => {
    allListbox.push(new MyListbox(elem.id));
  });

  Gazetter.register('record-form');
  Gazetter.init();

  const replaceNew = (elem, len) => {
    elem.id = elem.id.replace('__NEW__', `__NEW-${len}__`)
    elem.name = elem.name.replace('__NEW__', `__NEW-${len}__`)
  }

  // handle id create/remove
  const createIdButton = document.getElementById('create-identification');
  const identificationContainer = document.getElementById('identification-container');
  const tpl = document.getElementById('identification-template');

  let identificationCreated = 0;
  let id_assertion_ids = []
  createIdButton.onclick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    identificationCreated++;
    let tmp = tpl.firstElementChild.cloneNode(true);

    let idInputs = tmp.getElementsByClassName('id-input')
    let label = tmp.getElementsByClassName('id-input-label')[0]
    label.innerHTML = `NEW ${identificationCreated}`
    for (let input of idInputs) {
      if (['INPUT', 'SELECT', 'TEXTAREA'].indexOf(input.tagName) >= 0) {
        replaceNew(input, identificationCreated)
        if (input.hasAttribute('my-listbox')) {
          id_assertion_ids.push(input.id)
        }
      }
    }
    identificationContainer.appendChild(tmp)
    for (let id_ of id_assertion_ids) {
      allListbox.push(new MyListbox(id_));
    }
  }

  // handle unit create/remove
  const createUnitButton = document.getElementById('create-unit');
  const unitContainer = document.getElementById('unit-container');
  const unitTpl = document.getElementById('unit-template');

  let unitCreated = 0;
  let unit_assertion_ids = [];
  let unit_validations = [];
  createUnitButton.onclick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    unitCreated++;
    let tmp = unitTpl.firstElementChild.cloneNode(true);
    let unitInputs = tmp.getElementsByClassName('unit-input')
    let label = tmp.getElementsByClassName('unit-input-label')[0]
    label.innerHTML = `NEW ${unitCreated}`
    for (let input of unitInputs) {
      if (['INPUT', 'SELECT', 'TEXTAREA'].indexOf(input.tagName) >= 0) {
        replaceNew(input, unitCreated)
        if (input.hasAttribute('my-listbox')) {
          unit_assertion_ids.push(input.id)
        }
        if (input.hasAttribute('my-validate')) {
          unit_validations.push(input.id)
        }
      }
    }
    //let removeLink = tmp.children[2].children[0];
    //removeLink.onclick = (e) => {
    //  tmp.remove();
    //}
    unitContainer.appendChild(tmp);
    // must after unitContainer.appendChild
    for (let id_ of unit_assertion_ids) {
      allListbox.push(new MyListbox(id_));
    }
    for (let id_ of unit_validations) {
      allListbox.push(new MyValidate(id_));
    }
  }

  const deleteMacroItems = document.getElementsByClassName('record-macroitem-delete');
  //console.log(deleteMacroItems);
  for (let deleteBtn of deleteMacroItems) {
    deleteBtn.onclick = (e) => {
      e.preventDefault()
      if (confirm('確定刪除？') == true) {
        let itemWrapper = document.getElementById(`${e.target.dataset.type}__${e.target.dataset.item_id}__wrapper`)
        itemWrapper.remove();
      }
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
      //console.log(dmsLongitude);
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
