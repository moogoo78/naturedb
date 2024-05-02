/**
  filter (formValues), select2 struct:
  key: {
    value: value,
    display: display,
    name: name,
   }
*/

import { writable, get } from 'svelte/store';
import { fetchData, appendQuery } from './utils.js';
import { register, HOST } from './stores.js';

/* via: https://dmitripavlutin.com/how-to-compare-objects-in-javascript/  */
function shallowEqual(object1, object2) {
  const keys1 = Object.keys(object1);
  const keys2 = Object.keys(object2);

  if (keys1.length !== keys2.length) {
    return false;
  }

  for (let key of keys1) {
    //console.log(key, object1[key], object2[key], object1[key] !== object2[key]);
    if (Array.isArray(object1[key]) && Array.isArray(object1[key])) {
      if (object1[key].toString() !== object2[key].toString()) {
        return false;
      }
    } else {
      if (object1[key] !== object2[key]) {
        return false;
      }
    }
  }

  return true;
}

const initFormant = {
  searching: false,
  payload: {
    filter: {},
    range: [0, 20],
    sort: [],
    VIEW: 'table',
  },
  pagination: {
    page: 0,
    count: 0,
    perPage: 20,
  },
  tags: {},
  results: {},
  formValues: {},
  selectState: {
    group: {},
    option: {},
    loading: {},
  },
};

const makeFilterTags = (values) => {
  let tags = {};
  let registerData = get(register);
  // process payload filter to fetch
  let lowestTaxonIndex = -1;
  let intensive = {
    named_area__admin: {},
  };
  let extensive = {
    field_number: '',
    collect_date: '',
    altitude: '',
    accession_number: '',
  };
  let namedAreas = [];
  for (const [key, value] of Object.entries(values)) {
    if (value) {
      switch(key) {
      case 'adm1':
      case 'adm2':
      case 'adm3':
        intensive.named_area__admin[key] = value;
        break;
      case 'family':
      case 'genus':
      case 'species':
        // merge to lowest layer
        let selectedIndex = ['family', 'genus', 'species'].indexOf(key);
        if (selectedIndex > lowestTaxonIndex) {
          lowestTaxonIndex = selectedIndex;
          tags.taxon_id = {
            value: value,
            label: registerData[key].label,
            key: key,
          };
        }
        break;
      case 'field_number':
      case 'field_number2':
        extensive.field_number = values.field_number;
        if (values.field_number2) {
          extensive.field_number = `${extensive.field_number}--${values.field_number2}`;
        }
        break;
      case 'collect_date':
      case 'collect_date2':
        extensive.collect_date = values.collect_date;
        if (values.collect_date2) {
          extensive.collect_date = `${extensive.collect_date}--${values.collect_date2}`;
        }
        break;
      case 'altitude':
      case 'altitude2':
      case 'altitude_condiction':
        extensive.altitude = values.altitude;
        if (values.altitude_condiction
            && values.altitude_condiction === 'between'
            && values.altitude2) {
          extensive.altitude = `${extensive.altitude}--${values.altitude2}`;
        }
        if (values.altitude_condiction === 'gte') {
          extensive.altitude = `${extensive.altitude}--`;
        } else if (values.altitude_condiction === 'lte') {
          extensive.altitude = `--${extensive.altitude}`;
        }
        break;
      case 'accession_number':
      case 'accession_number2':
        extensive.accession_number = values.accession_number;
        if (values.accession_number2) {
          extensive.accession_number = `${extensive.accession_number}--${values.accession_number2}`;
        }
        break;
      default:
        if (value) {
          let param = registerData[key].param;
          tags[param] = {
            value: value,
            label: registerData[key].label,
            key: key
          };
        }
      }
    }
  }
  let naAdmTmp = {
    value: null,
    display: [],
  };
  for (const key of ['country', 'adm1', 'adm2', 'adm3']) {
    if (intensive.named_area__admin.hasOwnProperty(key)) {
      naAdmTmp.display.push(intensive.named_area__admin[key].display);
      naAdmTmp.value = intensive.named_area__admin[key].value;
    }
  }
  if (naAdmTmp.value) {
    tags.named_area__admin = {
      label: '行政區',
      value: {
        display: naAdmTmp.display.join('/'),
        value: naAdmTmp.value,
      },
      key: 'named_area__admin',
    };
  }
  for (const key in extensive) {
    if (extensive[key] !== '') {
      let text = extensive[key];
      let tlist = text.split('--');
      if (tlist[0] !== '' && tlist[1] !== '') {
        text = text.replace('--', ' - ');
      } else if (tlist[0] === '' && tlist[1] !== '') {
        text = `< ${tlist[1]}`;
      } else if (tlist[0] !== '' && tlist[1] === '') {
        text = `> ${tlist[0]}`;
      }
      tags[key] = {
        label: registerData[key].label,
        value: {
          display: text,
          value: extensive[key],
        },
        key: key,
      };
    }
  }
  return tags;
};

const createFormant = () => {

  const { subscribe, set, update } = writable(initFormant);

  async function goSearch(props) {
    //console.log('props', props);
    let ft = get(formant);
    let payload = {
      ...ft.payload,
      filter: {},  // update from formValues each search
    };
    let tags = {...ft.tags};
    let pagination = {...ft.pagination};
    let page = pagination.page;

    let named_area_id = [];
    let taxon_id = [];

    tags = makeFilterTags(ft.formValues);
    if (Object.keys(tags).length !== 0) {
      for (const [key, data] of Object.entries(tags)) {
        if (key.substring(0, 12) === 'named_area__') {
          named_area_id.push(data.value.value);
        } else if (['scientific_name', 'taxon_id'].indexOf(key) >= 0) {
          taxon_id.push(data.value.value);
        } else {
          payload.filter[key] = (typeof data.value === 'object') ? data.value.value : data.value;
        }
      }
      if (named_area_id.length > 0) {
        payload.filter.named_area_id = named_area_id;
      }
      if (taxon_id.length > 0) {
        payload.filter.taxon_id = taxon_id;
      }
    } else {
      payload.filter = {};
    }

    if (props?.page >= 0) {
      page = props.page;
      payload.range = [
      (props.page*pagination.perPage),
      ((props.page+1)*pagination.perPage)
      ];
    } else {
      page = 0;
      payload.range = initFormant.payload.range;
    }

    if( props?.sort) {
      payload.sort = [props.sort];
      page = 0;
    }
    if( props?.VIEW) {
      payload.VIEW = props.VIEW;
    }

    //console.log('payload', payload);
    let params = Object.entries(payload).map( (x) => {
      if (x[0] === 'VIEW') {
        return `VIEW=${x[1]}`;
      } else {
        return `${x[0]}=${JSON.stringify(x[1])}`;
      }
    });

    let queryString = params.join('&');
    let url = `${get(HOST)}/api/v1/search?${queryString}`;

    update( store => {
      return {
        ...store,
        searching: true
      };
    });

    let results = await fetchData(url);
    console.log('[goSearch] result:', results, payload);
    if (results && results.data) {
      update( store => {
        return {
          ...store,
          searching: false,
          payload: payload,
          results: results,
          tags: tags,
          pagination: {
            page: page,
            perPage: 20,
            count: results.total,
          },
          error: null,
        };
      });

      // if filter changed
      //console.log(ft.payload.filter, payload.filter, shallowEqual(ft.payload.filter, payload.filter));
      if (!shallowEqual(ft.payload.filter, payload.filter)) {
        const searchParams = new URLSearchParams(payload.filter);
        let qs = searchParams.toString();
        //let url = `${location.origin}`;
        let url = '/data';
        if (qs !== '') {
          url = `${url}?${qs}`;
        }
        history.pushState({}, "", url);
        //history.replaceState({}, "", url);
      }
    } else {
      update( store => {
        return {
          ...store,
          searching: false,
          payload: payload,
          results: {},
          tags: tags,
          pagination: {
            page: 0,
            perPage: 20,
            count: 0,
          },
          error: results,
        };
      });
    }
  };

  const findFormKey = (param) => {
    let registerData = get(register);
    for (let [key, data] of Object.entries(registerData)) {
      if (data.param === param) {
        return [key, data];
      }
    }
  };

  const findFunnel = (key) => {
    let registerData = get(register);
    let ft = get(formant);
    let selectState = {...ft.selectState};
    if (registerData[key].group?.name) {
      return selectState.group[registerData[key].group.name];
    }
  };

  const removeFilter = (props) => {
    let keys = Array.isArray(props) ? props : [props];
    update( pv => {
      let values = { ...pv.formValues };
      for (let key of keys) {
        delete values[key];
      }
      return {
        ...pv,
        formValues: values
      };
    });
  };

  const removeFilterWithFunnel = (props) => {
    let registerData = get(register);
    let ft = get(formant);
    let values = {...ft.formValues};

    let keys = Array.isArray(props) ? props : [props];

    for (let key of keys) {
      delete values[key];

      // funnel resets
      let funnel = findFunnel(key);
      if (funnel && funnel.indexOf(key) >= 0) {
        let selectedIndex = funnel.findIndex(x => key === x);
        funnel.slice(selectedIndex+1).forEach( x => {
          delete values[x];
        });
      }
      // extensive
      if (registerData[key].group?.type === 'extensive') {
        let extTo = registerData[key].group.to;
        if (values[extTo]) {
          delete values[extTo];
        }
      }
    }
    update( pv => {
      return {
        ...pv,
        formValues: values,
      };
    });
  };

  const addFilter = (props) => {
    update( pv => {
      return {
        ...pv,
        formValues: {
          ...pv.formValues,
          ...props,
        },
      };
    });
  };

  /* can add many filters */
  const addFilterWithFunnel = async (props) => {
    let registerData = get(register);
    let ft = get(formant);
    let values = {...ft.formValues};
    let selectState = {...ft.selectState};

    // funnel select & resets
    for (let key in props) {
      let funnel = findFunnel(key);
      if (funnel && funnel.indexOf(key) >= 0) {
        let selectedIndex = funnel.findIndex(x => key === x);
        // update next level options
        if ( selectedIndex >= 0 && selectedIndex <= funnel.length -2) {
          let target = funnel[selectedIndex+1];
          let qsArr = registerData[target].fetch.split('?');
          let searchParams = appendQuery(qsArr[1], 'filter', {parent_id: props[key].value});
          let url = `${get(HOST)}/${qsArr[0]}?${searchParams.toString()}`;
          selectState.loading[target] = true;
          let results = await fetchData(url);
          selectState.option[target] = results.data;
          selectState.loading[target] = false;
        }

        // reset group decent select options
        // selected next level is updated, so +2 reset
        if (selectedIndex < funnel.length - 2) {
          funnel.slice(selectedIndex+2).forEach( x => {
            selectState.option[x] = [];
            removeFilter(x);
          });
        }
      }
    }

    update( pv => {
      return {
        ...pv,
        formValues: {
          ...pv.formValues,
          ...props,
        },
        selectState: selectState,
      };
    });
  };

  const resetForm = () => {
    update( pv => {
      return {
        ...pv,
        formValues: {}
      };
    });
  };
  const searchFromSearchParams = async () => {
    const searchParams = new URLSearchParams(location.search);

    let values = {};
    let urls = [];
    searchParams.forEach((value, param) => {
      let [key, data] = findFormKey(param);
      if (data.type === 'combobox') {
        let qsArr = data.fetch.split('?');
        urls.push([key, `${get(HOST)}/${qsArr[0]}/${value}`]);
      } else {
        values[key] = value;
      }
    });
    const results = await Promise.all(urls.map(async ([key, url]) => {
      let results = await fetchData(url);
      values = {
        ...values,
        [key]: {
          value: results.id,
          display: results.display_name,
          name: key,
        }
      };
    }));

    if (Object.keys(values).length > 0) {
      resetForm();
      addFilterWithFunnel(values);
      goSearch();
    }
  };

  return {
    subscribe,
    set,
    update,
    goSearch,
    removeFilter,
    removeFilterWithFunnel,
    addFilter,
    addFilterWithFunnel,
    resetForm,
    searchFromSearchParams,
    findFunnel,
  };
}

export const formant = createFormant();
