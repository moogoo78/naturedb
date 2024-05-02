import { writable, readable, derived, get } from 'svelte/store';

export const HOST = readable(import.meta.env.VITE_HOST_URL);
//export const ftsResults = writable(null);

//export const filterTags = derived(formValuesSubmitted, ($formValues) => {
//taxon_id, collector_id, field_number--, collect_date--, collect_month, named_area_id, locality_text, altitude--, altitude_condiction, accession_number, accession_number2, type_status

const registerData = {
  "collector": {
    "id":"form-collector",
    "param": "collector_id",
    "label": "採集者",
    "type": "combobox",
    "fetch": `api/v1/people?filter={"is_collector":"1"}&sort=[{"name":""}]`,
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
    "fetch": `api/v1/taxa`,
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
    },
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
    },
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
  "continent": {
    "id":"form-continent",
    "label": "大洲",
    "type": "select",
    "param": "continent",
  },
  "country": {
    "param": "named_area_id",
    "label": "國家",
    "type": "combobox",
    "isFetchInit": true,
    "fetch": `api/v1/named-areas?filter={"area_class_id":"7"}`,
    "group": {
      "name": "named_area__admin",
      "type": "intensive",
      "index": 0,
      "removeIndependent": true,
    }
  },
  "adm1": {
    "param": "named_area_id",
    "label": "行政區1",
    "type": "combobox",
    "fetch": `api/v1/named-areas?filter={"area_class_id":"8"}`,
    "group": {
      "name": "named_area__admin",
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
      "name": "named_area__admin",
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
      "name": "named_area__admin",
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
