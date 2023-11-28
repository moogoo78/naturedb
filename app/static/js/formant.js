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
     autocomplete related render is customize only
 */

const  Formant = (()=> {
  const pub = {};
  let form = null;
  let data = {};
  let helpers = {};

  const _renderOptions = (element, options, value, text) => {
    element.innerHTML = '<option value="">-- choose --</option>';
    options.forEach( v => {
      const option = document.createElement('option');
      option.value = v[value];
      option.innerHTML = v[text];
      element.appendChild(option);
    });
  };

  const _findEntitiesByKey = (key) => {
    if (data[key].entities) { // typeGroup
      return data[key].entities;
    } else {
      return [data[key]];
    }
  }

  const _findEntityByName = (name) => {
    for (const k in data) {
      if (data[k].entities) { // typeGroup
        for (const i in data[k].entities) {
          if (data[k].entities[i][1].element.name === name) {
            return data[k].entities[i][1];
          }
        }
      } else {
        if (data[k].element.name === name) {
          return data[k];
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
            data[args.key] = entity;
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
      data[key] = {
        groupType: 'intensive',
        entities: sorted,
      }
    }
    // sort by extensive: {number}
    for (const key in extensiveSets) {
      const sorted = extensiveSets[key].sort((a, b) => a[0] - b[0]);
      data[key] = {
        groupType: 'extensive',
        entities: sorted,
      }
    }
    //console.log(data);
  };

  pub.setHelpers = (helper, func) => {
    helpers[helper] = func;
  };

  pub.setOptions = (options) => {
    const fetchEntities = [];
    for (const k in data) {
      if (data[k].entities) { // typeGroup
        for (const i in data[k].entities) {
          if ('fetch' in data[k].entities[i][1].args) {
            fetchEntities.push(data[k].entities[i][1]);
          }
        }
      } else if (data[k].args.fetch) {
        fetchEntities.push(data[k]);
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
    const entities = _findEntitiesByKey(key);
    for (const ent of entities) {
      ent.element.value = '';
    }
  }
  pub.addFilter = (key, value, index) => {
    const formData = _getFormData();
    const entities = _findEntitiesByKey(key);
    //console.log(data, key, value, entities);
    /*
    for (const i in entities) {
      if (index !== undefined) {
        console.log(index, i, entities[i][1].element.name, value);
        if (parseInt(i) === parseInt(index)) {
          entities[i][1].element.value = value;
          formData.set(entities[i][1].element.name, value);
          console.log('set', value,entities[i][1].element.value );
          //data[key].entities[i][1].element.value = value;
          //console.log(data[key].entities[i][1].element);
          //const foo = document.getElementById(entities[i].element.id);
          //foo.value = value;
          //console.log(foo);

        } else {
          entities[i][1].element.value = '';
        }
      } else {
        if (parseInt(i) === 0) {
          entities[0].element.value = value;
          //formData.set(entities[0].element.name, value);
        } else {
          entities[i].element.value = '';
        }
      }
    }
    */
    console.log(data[key]);
    //console.log(entities);
  }

  pub.getFilterSet = () => {
    const formData = _getFormData();
    let keys = {};
    let tokens = {};
    for (const k in data) {
      if (data[k].entities) { // typeGroup
        if (data[k].groupType === 'intensive') {
          // get most intensive only
          for (const i in data[k].entities) {
            const name = data[k].entities[i][1].element.name;
            if (formData.get(name)) {
              keys[k] = formData.get(name);
              break;
            }
          }
        } else if (data[k].groupType === 'extensive') {
          const name1 = data[k].entities[0][1].element.name;
          const name2 = data[k].entities[1][1].element.name;
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
          const value = formData.get(data[k].element.name);
          if (value) {
            keys[k] = value;
          }
        }
      }
    }
    return keys
  };
  return pub;
})();

export default Formant;


