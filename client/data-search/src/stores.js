import { writable, readable, derived, get } from 'svelte/store';
import { fetchData } from './lib/utils.js';

export const HOST = readable(import.meta.env.VITE_HOST_URL);
//export const ftsResults = writable(null);
export const formValues = writable({}); // easy to control form values, so dependent from formant
export const currentPage = writable(0);

const makeFilterTags = (values) => {
  let tags = {};

  // process payload filter to fetch
  let taxon = {index: -1, value: null};
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
        // 只留最下層
        let intensiveIndex = ['family', 'genus', 'species'].indexOf(key);
        if (intensiveIndex > taxon.index) {
          taxon = {
            index: intensiveIndex,
            value: value.value,
          };
          tags.taxon_id = {
            value: {
              value: taxon.value,
              display: value.display,
            },
            label: registerData[key].label,
          };
        }
        break;
      case 'collector':
        tags.collector_id = {
          value: value,
          label: registerData[key].label,
        };
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
          tags[key] = {
            value: value,
            label: registerData[key].label,
          };
        }
      }
    }
  }
  let naAdmTmp = {
    value: null,
    display: [],
  };
  for (const key of ['adm1', 'adm2', 'adm3']) {
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
      }
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
        }
      };
    }
  }
  return tags;
};

//export const filterTags = derived(formValuesSubmitted, ($formValues) => {
//taxon_id, collector_id, field_number--, collect_date--, collect_month, named_area_id, locality_text, altitude--, altitude_condiction, accession_number, accession_number2, type_status

const registerData = {
  "continent": {
    "id":"form-continent",
    "label": "大洲",
    "type": "select",
    "fetch": `api/v1/named-areas?filter={"area_class_":"7"}&range=[0, 500]`,
  },
  "collector": {
    "id":"form-collector",
    "label": "採集者",
    "type": "combobox",
    "fetch": `api/v1/people?filter={"is_collector":"1"}&sort=[{"name":""}]&range=[0,100]`,
    "isFetchInit": true,
  },
  "field_number": {
    "id":"form-field-number",
    "param": "field_number",
    "label": "採集號",
    "type": "input",
    "group": {
      "name": "field_number",
      "type": "extensive",
      "to": "field_number2"
    }
  },
  "scientific_name": {
    "param": "scientific_name",
    "label": "學名",
    "type": "combobox",
    "fetch": `api/v1/taxa?&range=[0, 500]`,
  },
  "family": {
    "param": "taxon_id",
    "label": "科名(Family)",
    "type": "combobox",
    "fetch": `api/v1/taxa?filter={"rank":"family"}&range=[0,600]`,
    "isFetchInit": true,
    "group": {
      "name": "taxon",
      "type": "intensive",
      "index": 0,
    }
  },
  "genus": {
    "label": "屬名(Genus)",
    "param": "taxon_id",
    "type": "combobox",
    "fetch": `api/v1/taxa?filter={"rank":"genus"}&range=[0, 600]`,
    "group": {
      "name": "taxon",
      "type": "intensive",
      "index": 1,
    }
  },
  "species": {
    "label": "種名(Species)",
    "param": "taxon_id",
    "type": "combobox",
    "fetch": `api/v1/taxa?filter={"rank":"species"}&range=[0, -1]`,
    "group": {
      "name": "taxon",
      "type": "intensive",
      "index": 2,
    }
  },
  "country": {
    "param": "named_area_id",
    "label": "國家",
    "type": "combobox",
    "isFetchInit": true,
    "fetch": `api/v1/named-areas?filter={"area_class_id":"7"}`,
    "group": {
      "name": "named_area",
      "type": "intensive",
      "index": 0,
    }
  },
  "adm1": {
    "param": "named_area_id",
    "label": "行政區1",
    "type": "combobox",
    "fetch": `api/v1/named-areas?filter={"area_class_id":"8"}`,
    "group": {
      "name": "named_area",
      "type": "intensive",
      "index": 1,
    }
  },
  "adm2": {
    "param": "named_area_id",
    "label": "行政區2",
    "type": "combobox",
    "fetch": `api/v1/named-areas?filter={"area_class_id":"9"}`,
    "group": {
      "name": "named_area",
      "type": "intensive",
      "index": 2,
    }
  },
  "adm3": {
    "param": "named_area_id",
    "label": "行政區3",
    "type": "combobox",
    "fetch": `api/v1/named-areas?filter={"area_class_id":"10"}`,
    "group": {
      "name": "named_area",
      "type": "intensive",
      "index": 3,
    }
  },
  "named_area__park": {
    "param": "named_area_id",
    "label": "國家公園/保護留區",
    "type": "combobox",
    "isFetchInit": true,
    "fetch": `api/v1/named-areas?filter={"area_class_id":"5"}`,
  },
  "named_area__locality": {
    "param": "named_area_id",
    "label": "地點名稱",
    "type": "combobox",
    "isFetchInit": true,
    "fetch": `api/v1/named-areas?filter={"area_class_id":"6"}`,
  },
  "collect_date": {
    "label": "採集日期",
    "param": "collect_date",
    "type": "date",
    "group": {
      "name": "collect_date",
      "type": "extensive",
      "to": "collect_date2"
    }
  },
  "collect_month": {
    "label": "採集月份",
    "param": "collect_month",
    "type": "select",
  },
  "altitude": {
    "label": "海拔",
    "param": "altitude",
  },
  "altitude_condition": {
    "param": "altitude_condition",
  },
  "accession_number": {
    "label": "館號",
    "param": "accession_number",
    "group": {
      "name": "accession_number",
      "type": "extensive",
      "to": "accession_number2"
    }
  },
  "accession_number2": {
    "label": "館號",
    "param": "accession_number2",
  },
  "type_status": {
    "label": "模式標本",
    "param": "type_status",
  }
};

export const register = readable(registerData);

const initFormant = {
  searching: false,
  payload: {
    filter: {},
    range: [0, 20],
    sort: [],
  },
  pagination: {
    page: 0,
    count: 0,
    perPage: 20,
  },
  tags: {},
  results: {},
};

const createFormant = () => {

  const { subscribe, set, update } = writable(initFormant);

  async function goSearch(props) {
    //console.log('props', props);
    let ft = get(formant);
    let payload = {...ft.payload};
    let tags = {...ft.tags};
    let pagination = {...ft.pagination};
    let page = pagination.page;

    let named_area_id = [];
    let taxon_id = [];

    if (props?.formValues) {
      tags = makeFilterTags(props.formValues);
      console.log(tags);
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

    //console.log('payload', payload);
    let params = Object.entries(payload).map( (x) => {
      return `${x[0]}=${JSON.stringify(x[1])}`;
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
    console.log('[goSearch] result:', results);
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

  return {
    subscribe,
    set,
    update,
    goSearch,
  };
}

export const formant = createFormant();
//export const formant = writable(initFormant);



