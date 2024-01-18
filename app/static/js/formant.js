// tokens跟schema很重疊
// formData跟schema的關係

/**
 * =========================
 * Formant JavaStript Module
 * =========================
 * for process form element, submit, filter tokens
 *
 * inspired from UIkit framework (like Web Component)
 *
 * fetch API rules:
 *   api/filter={filterObject}&sort=[{field_name, -desc_field_name}]&range=[0, -1]
 * - filter: object (by key)
 * - sort: Array of sorted by field name (prefix with "-" for DESC)
 * - range: [start, end], if  [0,1] means no limit
 *
 * arguments:
 * - key: {filter key}
 * - label: {label}
 * - fetch: {API url}
 * - isFetchInit: fetch options initially
 * - query: {query string}
 * - sort: [foo, -bar]
 * - optionValue: {id}
 * - optionText: {text}
 * - changeTarget: {number} (needed for intensive)
 * - intensive|extensive: {number}, extensive use as range
 * - autocomplete: {q} (query field)
 *   autocomplete related render is customize only
 * - refName: refercence form name (for autocomplete id input)
 *
 * addFilter/removeFilter is to set formData value
 */

const  Formant = (()=> {
  const pub = {};
  let form = null;
  let schema = {}; // all rules save here!
  let helpers = {};
  let initEntityFunctions = [];
  let selectCallbacks = {};
  let searchParams = {
    "filter": null,
    "range": null,
    "sort": null
  };
  let tokensWithLabel = {};

  const _renderOptions = (element, options, value, text, selectedId) => {
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

  const _findLabel = (key) => {
    if (schema[key].entities) { // typeGroup
      return schema[key].entities[0][1].args.label;
    } else {
      return schema[key].args.label;
    }
  }

  const _findEntitiesByKey = (key) => {
    if (schema[key].entities) { // typeGroup
      return schema[key].entities;
    } else {
      return [schema[key]];
    }
  }

  const _findEntityByName = (name) => {
    for (const k in schema) {
      if (schema[k].entities) { // typeGroup
        for (const i in schema[k].entities) {
          if (schema[k].entities[i][1].element.name === name) {
            return schema[k].entities[i][1];
          }
        }
      } else {
        if (schema[k].element.name === name) {
          return schema[k];
        }
      }
    }
  }

  const _makeFetchUrl = (entity, appendQuery) => {
    const queryList = [];
    if ('query' in entity.args) {
      const filterParams = new URLSearchParams(entity.args.query);
      let params = Object.fromEntries(filterParams);
      if (appendQuery) {
        const pair = appendQuery.split('=');
        params = {
          ...params,
          [pair[0]]: pair[1],
        }
      }
      queryList.push(`filter=${JSON.stringify(params)}`);
    }
    if ('sort' in entity.args) {
      const sort = entity.args.sort.split(',').map(v => {
        return (v[0] === '-') ? {[v.substr(1)]:'desc'} : {[v]:''};
      });
      queryList.push(`sort=${JSON.stringify(sort)}`);
    }
    if ('range' in entity.args) {
      const range = JSON.parse(entity.args.range);
      queryList.push(`range=${JSON.stringify(range)}`);
    }
    let url = `${entity.args.fetch}`;
    if (queryList.length) {
      url = `${url}?${queryList.join('&')}`;
    }
    return url
  };

  const _bindEvent = (entity, func=undefined) => {
    const events = [];
    if ('changeTarget' in entity.args) {
      events.push('changeTarget');
    }
    if ('isFetchInit' in entity.args) {
      //events.push('init');
      initEntityFunctions.push([entity, func]);
    }
    if ('autocomplete' in entity.args) {
      events.push('autocomplete');
    }

    events.forEach( eventType => {
      switch (eventType) {
        case 'autocomplete':
          entity.element.addEventListener("input", (event) => {
            let url = _makeFetchUrl(entity, `${entity.args.autocomplete}=${event.target.value}`);
            helpers.fetch(url)
                   .then(resp => {
                     //console.log(resp);
                     if (func) {
                       func(entity, resp.data);
                     } else {
                       // TODO
                     }
                   });
          })
          break;
        //case 'init':
        //  let url = _makeFetchUrl(entity);
        //  helpers.fetch(url)
        //         .then(resp => {
        //           if (func) {
        //             func(entity.element, resp.data);
        //           } else {
        //             _renderOptions(entity.element, resp.data, entity.args.optionValue, entity.args.optionText);
        //           }
        //         });
        //  break;
        case 'changeTarget':
          entity.element.addEventListener("change", (event) => {
            let query = {};
            const targetEntity = _findEntityByName(entity.args.changeTarget);
            let targetUrl = _makeFetchUrl(targetEntity, entity.args.changeTargetQuery.replace('this.value', event.currentTarget.value));
            helpers.fetch(targetUrl)
                   .then(resp => {
                     if (func) {
                       func(targetEntity.element, resp.data);
                     } else {
                       _renderOptions(targetEntity.element, resp.data, targetEntity.args.optionValue, targetEntity.args.optionText);
                     }
                   });
          });
          break;
        default:
          break;
      };
    });
  }

  const _setOptions = (options) => {
    selectCallbacks = options.selectCallbacks;

    // find element need fetch, set by element not only setOptions
    const fetchEntities = []; // selectCallbacks
    for (const k in schema) {
      if (schema[k].entities) { // typeGroup
        for (const i in schema[k].entities) {
          if ('fetch' in schema[k].entities[i][1].args) {
            fetchEntities.push(schema[k].entities[i][1]);
          }
        }
      } else if (schema[k].args.fetch) {
        fetchEntities.push(schema[k]);
      }
    }

    for (const [option, data] of Object.entries(options)) {
      switch(option) {
        case 'helpers':
          for (const [helper, func] of Object.entries(data)) {
            helpers[helper] = func;
          }
          break;
        case 'selectCallbacks':
          fetchEntities.forEach( entity => {
            const key = entity.args.key;
            if (data.hasOwnProperty(key)) {
              _bindEvent(entity, data[key]);
            } else {
              _bindEvent(entity);
            }
          });
          break;
        case 'intensiveRelation':
          for (const [key, relation] of Object.entries(data)) {
            schema[key].relation = relation;
          }
          break;
      }
    }
  };

  const register = (formId, options) => {
    form = document.getElementById(formId);
    let intensiveSets = {};
    let extensiveSets = {};
    for (const i in form.elements) {
      const input = form.elements[i];
      if (input.nodeName && input.hasAttribute('formant')) {
        // parse attribute(string) to args(object)
        const attrs = input.getAttribute('formant');
        let args = {};
        attrs.split(';').filter( x => x.length > 0).forEach( x => {
          let [k, v] = x.split(':');
          args[k.trim()] = (v && v.trim()) ||  '';
        });

        if (['INPUT', 'SELECT'].indexOf(input.nodeName) >= 0) {
          //console.log(input);
          let entity = {
            id: input.id,
            element: document.getElementById(input.id),
            value: input.value,
            args: args,
          };

          if (args.hasOwnProperty('intensive')) {
            if (!intensiveSets.hasOwnProperty(args.key)) {
              intensiveSets[args.key] = [];
            }
            intensiveSets[args.key].push([parseInt(args.intensive), entity]);
          } else if (args.hasOwnProperty('extensive')) {
            if (!extensiveSets.hasOwnProperty(args.key)) {
              extensiveSets[args.key] = [];
            }
            extensiveSets[args.key].push([parseInt(args.extensive), entity]);
          } else {
            schema[args.key] = entity;
          }
        }
        /* else if (input.nodeName === 'BUTTON'){
         *   input.onclick = (e) => {
         *     e.preventDefault();
         *     console.log(args);
         *   }
         * } */
      }
    }
    // sort by intensive: {number}
    for (const key in intensiveSets) {
      const sorted = intensiveSets[key].sort((a, b) => a[0] - b[0]);
      schema[key] = {
        groupType: 'intensive',
        entities: sorted,
      }
    }
    // sort by extensive: {number}
    for (const key in extensiveSets) {
      const sorted = extensiveSets[key].sort((a, b) => a[0] - b[0]);
      schema[key] = {
        groupType: 'extensive',
        entities: sorted,
      }
    }

    _setOptions(options);
    return schema;
  };

  const init = async function _init() {
    for (const item of initEntityFunctions) {
      const entity = item[0];
      const func = item[1];
      const url = _makeFetchUrl(entity);
      await helpers.fetch(url)
             .then(resp => {
               if (func) {
                 func(entity.element, resp.data);
               } else {
                 _renderOptions(entity.element, resp.data, entity.args.optionValue, entity.args.optionText);
               }
             });
    }
  }


  const _processIntensiveClosureTable = (result, relation, higher, key, value) => {
    let depth = -1; // depth after current hiararchy (category)
    let currentIndex = -1;
    for (let i=schema[key].entities.length-1; i>=0; i--) {
      const entity = schema[key].entities[i][1];
      const cat = entity.args.query.split('=')[1];
      const isCurrentLayer = (String(cat) === String(result[relation.categoryName])) ? true : false;
      if (depth >= 0) {
        depth++;
      }
      if (isCurrentLayer === true) {
        depth = 0;
        //currentIndex = schema[key].entities.length -1 - i;
        currentIndex = i;
      }
      //console.log(i, entity.id, depth);
      if (i === schema[key].entities.length-1) {
        // highest hirearchy
        entity.element.value = (higher.length > 0) ? higher[0].id : value;
      } else if (depth < 2) {
        const optionData = result[relation.optionPath][cat];
        let selectedId = null;
        if (selectCallbacks.hasOwnProperty(key)) {
          // custom render function
          selectCallbacks[key](entity.element, optionData);
        } else {
          if (higher.length > 0) {
            selectedId = (isCurrentLayer === true) ? result.id : higher[i].id;
          }
          _renderOptions(
            entity.element,
            optionData,
            entity.args.optionValue,
            entity.args.optionText,
            selectedId,
          )
        }
      }
    }
    return currentIndex;
  }

  const _processIntensiveAdjacencyList = (result, relation, higher, key, value) => {
    //console.log(result, higher);
    let depth = -1; // depth after current hiararchy (category)
    let currentIndex = -1;
    for (let i=schema[key].entities.length-1; i>=0; i--) {
      const entity = schema[key].entities[i][1];
      const cat = entity.args.query.split('=')[1];
      const isCurrentLayer = (String(cat) === String(result[relation.categoryName])) ? true : false;
      if (depth >= 0) {
        depth++;
      }
      if (isCurrentLayer === true) {
        depth = 0;
        //currentIndex = schema[key].entities.length -1 - i;
        currentIndex = i;
      }
      //console.log(i, depth, isCurrentLayer);
      if (i === schema[key].entities.length-1) {
        // highest hirearchy
        entity.element.value = (higher.length > 0) ? higher[0].id : value;
      } else if (depth < 2) {
        const optionData = result[relation.optionPath][String(cat)];
        let selectedId = null;
        if (selectCallbacks.hasOwnProperty(key)) {
          // custom render function
          selectCallbacks[key](entity.element, optionData);
        } else {
          if (higher.length > 0 && schema[key].entities.length -i -1<= higher.length) {
            if (isCurrentLayer === true) {
              selectedId = result.id;
            } else if (depth < 0) {
              selectedId =higher[schema[key].entities.length - i - 1].id;
            }
          }
          if (optionData && optionData.length > 0) {
            _renderOptions(
              entity.element,
              optionData,
              entity.args.optionValue,
              entity.args.optionText,
              selectedId,
            )
          }
        }
      }
    }
    return currentIndex;
  }

  const setFilters = async function _setFilters(filters) {
    let tokens = {}; // append label & displayValue to filters
    searchParams.filter = filters;

    for (const [key, value] of Object.entries(filters)) {
      const relation = schema[key].relation;
      const label = ('groupType' in schema[key])
            ? schema[key].entities[0][1].args.label
            : schema[key].args.label;
      let displayValue = value;
      if (schema[key].groupType === 'intensive' && schema[key].entities.length > 0) {
        let entityIndex = -1;
        let options = null;
        const res = await helpers
              .fetch(`${schema[key].entities[0][1].args.fetch}/${value}?${relation.childrenQuery}`)
              .then( result => {
                //console.log(result);
                const higher = result[relation.higherCategory];
                switch (relation.model) {
                case 'closureTable':
                  entityIndex = _processIntensiveClosureTable(result, relation, higher, key, value);
                  options = schema[key].entities[entityIndex][1].element.options;
                  displayValue = options[options.selectedIndex].text;
                  break;
                case 'adjacencyList':
                  entityIndex = _processIntensiveAdjacencyList(result, relation, higher, key, value);
                  options = schema[key].entities[entityIndex][1].element.options;
                  displayValue = options[options.selectedIndex].text;
                  break;
                }
              });
      } else if (schema[key].groupType === 'extensive') {
        for (const i in schema[key].entities) {
          if (parseInt(i) === 0) {
            schema[key].entities[i][1].element.value = value;
          } else {
            schema[key].entities[i][1].element.value = '';
          }
        }
      } else {
        schema[key].element.value = value;

        if ('refName' in schema[key].args) {
          const ref = _findEntityByName(schema[key].args.refName);
          const res = await helpers
                .fetch(`${ref.args.fetch}/${value}`)
                .then( resp => {
                  displayValue = resp[ref.args.optionText];
                  ref.value = displayValue;
                  schema[ref.args.key].element.value = displayValue;
                });
        }
      }
      tokens[key] = {
        label: label,
        value: value,
        displayValue: displayValue,
      }
    }
    //return tokens;
    tokensWithLabel = tokens;

    return await search();
  };

  const search = async function _search() {
    const queryList = [];
    for(const key in searchParams) {
      if (searchParams[key]) {
        queryList.push(`${key}=${JSON.stringify(searchParams[key])}`);
      }
    }
    const queryString = queryList.join('&');
    let url = `/api/v1/search`;
    if (queryString) {
      url = `${url}?${queryString}`;
    }
    return await helpers.fetch(url).then((resp) => { return resp; });
  }

  const addFilters = (newFilters) => {
    let filters = _getFilters();
    let availFilters = {};
    for (const k in newFilters) {
      if (k.indexOf('__exclude') < 0) {
        availFilters[k] = newFilters[k];
      }
    }
    filters = {
      ...filters,
      ...availFilters,
    };
    return setFilters(filters);
  };

  const removeFilter = (key) => {
    if ('groupType' in schema[key]) {
        for (const i in schema[key].entities) {
          schema[key].entities[i][1].element.value = '';
        }
    } else {
      schema[key].element.value = '';
    }
    let filters = _getFilters();
    return setFilters(filters);
  }

  const _getFilters = () => {
    const formData = new FormData(form);
    let keys = {};
    let tokens = {};
    for (const k in schema) {
      if (schema[k].entities) { // typeGroup
        if (schema[k].groupType === 'intensive') {
          // get most intensive only
          for (const i in schema[k].entities) {
            const name = schema[k].entities[i][1].element.name;
            if (formData.get(name)) {
              keys[k] = formData.get(name);
              break;
            }
          }
        } else if (schema[k].groupType === 'extensive') {
          const name1 = schema[k].entities[0][1].element.name;
          const name2 = schema[k].entities[1][1].element.name;
          // get range
          const start = formData.get(name1);
          const end = formData.get(name2);
          if (start) {
            keys[k] = start;
            if (end) {
              keys[k] = `${start}--${end}`;
            }
          }
        }
      } else {
        if (k.indexOf('__exclude') < 0) {
          const value = formData.get(schema[k].element.name);
          if (value) {
            keys[k] = value;
          }
        }
      }
    }
    return keys
  }; // end of _getFilters


  const getTokens = () => {
    return tokensWithLabel;
  }
  const setSearchParams = (params) => {
    searchParams = {
      ...searchParams,
      ...params,
    }
  };

  return { register, init, setFilters, removeFilter, addFilters, search, getTokens, setSearchParams};
})();

export default Formant;


