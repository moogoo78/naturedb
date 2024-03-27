import { writable, readable, derived } from 'svelte/store';

export const HOST = readable(import.meta.env.VITE_HOST_URL);
export const searching = writable(false);
export const ftsResults = writable(null);
export const unitResults = writable({});
export const isSidebarOpen = writable(true);
export const isLanding = writable(true);
export const currentPage = writable(0);
export const pagination = writable({
  page: 0,
  count: 0,
  perPage: 0,
});
export const formValues = writable({});
export const filterTags = derived(formValues, ($formValues) => {
  //taxon_id, collector_id, field_number--, collect_date--, collect_month, named_area_id, locality_text, altitude--, altitude_condiction, accession_number, accession_number2, type_status
  let tags = {};
  // process payload filter to fetch
  let taxon = {index: -1, value: null};
  let namedArea = {index: -1, value: null};
  let extensive = {
    field_number: '',
    collect_date: '',
    altitude: '',
  };
  let collectDates = '';
  for (const [key, value] of Object.entries($formValues)) {
    if (value) {
      switch(key) {
      case 'family':
      case 'genus':
      case 'species':
        let taxonIndex = ['family', 'genus', 'species'].indexOf(key);
        if (taxonIndex > taxon.index) {
          tags.taxon_id = {
            value: value,
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
        extensive.field_number = $formValues.field_number;
        if ($formValues.field_number2) {
          extensive.field_number = `${extensive.field_number}--${$formValues.field_number2}`;
        }
        break;
      case 'collect_date':
      case 'collect_date2':
        extensive.collect_date = $formValues.collect_date;
        if ($formValues.collect_date2) {
          extensive.collect_date = `${extensive.collect_date}--${$formValues.collect_date2}`;
        }
        break;
      case 'altitude':
      case 'altitude2':
        extensive.altitude = $formValues.altitude;
        if ($formValues.altitude2) {
          extensive.altitude = `${extensive.altitude}--${$formValues.altitude2}`;
        }
        break;
      default:
        if (value) {
          tags[key] = {
            value: value,
            label: registerData[key].label,
            name: key,
          };
        }
      }
    }
  }
  for (const key in extensive) {
      if (extensive[key] !== '') {
        tags[key] = {
          label: registerData[key].label,
          value: extensive[key].replace('--', ' - '),
        };
      }
  }

  return tags;
});



const registerData = {
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
    "type": "input"
  },
  "family": {
    "param": "taxon_id",
    "label": "科名(Family)",
    "type": "combobox",
    "fetch": `api/v1/taxa?filter={"rank":"family"}&sort=[{"full_scientific_name":""}]&range=[0,600]`,
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
    "fetch": `api/v1/taxa?filter={"rank":"genus"}&sort=[{"full_scientific_name":""}]&range=[0, 600]`,
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
    "fetch": `api/v1/taxa?filter={"rank":"species"}&sort=[{"full_scientific_name":""}]&range=[0, 600]`,
    "group": {
      "name": "taxon",
      "type": "intensive",
      "index": 2,
    }
  },
  "country": {
    "param": "named_area_id",
    "type": "combobox",
    "isFetchInit": true,
    "fetch": `api/v1/named-areas?filter={"area_class_id":"7"}&range=[0, 500]`,
    "group": {
      "name": "named_area",
      "type": "intensive",
      "index": 0,
    }
  },
  "adm1": {
    "param": "named_area_id",
    "type": "combobox",
    "fetch": `api/v1/named-areas?filter={"area_class_id":"2"}&range=[0, 500]`,
    "group": {
      "name": "named_area",
      "type": "intensive",
      "index": 1,
    }
  },
  "adm2": {
    "param": "named_area_id",
    "type": "combobox",
    "fetch": `api/v1/named-areas?filter={"area_class_id":"3"}&range=[0, 500]`,
    "group": {
      "name": "named_area",
      "type": "intensive",
      "index": 2,
    }
  },
  "collect_date": {
    "label": "採集日期",
    "param": "collect_date",
    "type": "date",
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
