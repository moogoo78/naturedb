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
 */

const  Formant = (()=> {
  const pub = {};
  let form = null;
  let schema = {};
  let helpers = {};

  const _renderOptions = (element, options, value, text) => {
    element[0] = new Option('-- choose --', '', true, true);
    options.forEach( (v, i) => {
      element[i+1] = new Option(v[text], v[value], false);
    });
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
      events.push('init');
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
                     console.log(resp);
                     if (func) {
                       func(entity, resp.data);
                     } else {
                       // TODO
                     }
                   });
          })
          break;
        case 'init':
          let url = _makeFetchUrl(entity);
          helpers.fetch(url)
                 .then(resp => {
                   if (func) {
                     func(entity.element, resp.data);
                   } else {
                     _renderOptions(entity.element, resp.data, entity.args.optionValue, entity.args.optionText);
                   }
                 });
          break;
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

  const _getFormData = () => {
    return new FormData(form);
  };

  pub.getFormData = () => {
    return new FormData(form);
  }
  pub.register = (formId) => {
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
    //console.log(schema);
  };

  pub.setHelpers = (helper, func) => {
    helpers[helper] = func;
  };

  pub.setOptions = (options) => {
    const fetchEntities = [];
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

    fetchEntities.forEach( entity => {
      if (options
          && 'selectCallbacks' in options
          && entity.args.key in options.selectCallbacks) {
        _bindEvent(entity, options.selectCallbacks[entity.args.key]);
      } else {
        _bindEvent(entity);
      }
    });
  };

  pub.removeFilter = (key) => {
    if ('groupType' in schema[key]) {
        for (const i in schema[key].entities) {
          schema[key].entities[i][1].element.value = '';
        }
    } else {
      schema[key].element.value = '';
    }
  }

  pub.addFilter = (key, value, index) => {
    if (schema[key].groupType === 'intensive') {
      /*
      for (const i in schema[key].entities) {
        if (parseInt(i) === parseInt(index)) {
          schema[key].entities[i][1].element.value = value;
        } else {
          schema[key].entities[i][1].element.value = '';
        }
      }
      */
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
    }
    console.log(schema[key]);
  }

  pub.getFilterSet = () => {
    const formData = _getFormData();
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
  }; // end of getFilterSet

  pub.getTokens = (keys) => {
    const tokens = [];
    const fetchList = [];
    for (const [k, v] of Object.entries(keys)) {
      const label = ('groupType' in schema[k])
                  ? schema[k].entities[0][1].args.label
                  : schema[k].args.label;
      if ('groupType' in schema[k]) {
        if ('fetch' in schema[k].entities[0][1].args) {
          //console.log(k, schema[k].entities[0][1].args.fetch);
          const url = `${schema[k].entities[0][1].args.fetch}/${v}`;
          fetchList.push([k, url])
        }
      } else {
        if ('refName' in schema[k].args) {
          const ref = _findEntityByName(schema[k].args.refName);
          //console.log(k, ref.args.fetch);
          const url = `${ref.args.fetch}/${v}`
          fetchList.push([k, url]);
        }
      }
      tokens.push({
        key: k,
        label: label,
        value: v,
      });
    }

    return Promise
      .all(fetchList.map( x => helpers.fetch(x[1])))
      .then( resp => {
        const resMap = {};
        resp.forEach( (v, i) => {
          resMap[fetchList[i][0]] = v;
        });
        const displayTokens = tokens.map( x => {
          const item = { ...x };
          if (x.key in resMap) {
            item.displayValue = resMap[x.key].display_name; // TODO, display_name by config
          }
          return item;
        });
        return displayTokens;
      });
  }; // end of getTokens
  return pub;
})();

export default Formant;


