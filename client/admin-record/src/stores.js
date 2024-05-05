import { writable, readable, derived, get } from 'svelte/store';
import { fetchData } from './utils.js';

export const HOST = readable(import.meta.env.VITE_HOST_URL);
export const hasError = writable('');

const reModify = /^\/admin\/collections\/(\d+)\/records\/(\d+)/.exec(document.location.pathname);
const reCreate = /^\/admin\/collections\/(\d+)/.exec(document.location.pathname);
if (reCreate === null) {
  alert('collection/record url error');
}
export const COLLECTION_ID = readable((reModify) ? reModify[1] : reCreate[1]);
export const RECORD_ID = readable((reModify) ? reModify[2] : null);

const getOptions = async () => {
  let url = `${get(HOST)}/api/v1/admin/collections/${get(COLLECTION_ID)}/options`;
  return await fetchData(url);
};

let result = await getOptions();
let aTypeRocord = [];
let aTypeUnit = [];

const getValues = async () => {
  let url = `${get(HOST)}/api/v1/admin/collections/${get(COLLECTION_ID)}/records/${get(RECORD_ID)}`;
  let results = await fetchData(url);
  if (typeof(results) === 'object') {
    hasError.set('');
    return results;
  } else if (typeof(results) === 'string') {
    hasError.set(results);
  }
};

let ret = {
  ...result,
  project_list: result.project_list,
  collector_list: result.person_list.filter( (x) => (x.is_collector) ? true : false),
  identifier_list: result.person_list.filter( (x) => (x.is_identifier) ? true : false),
  person_list: result.person_list,
};
delete result.person_list;
export const allOptions = readable(ret);
export const values = readable((reModify) ? await getValues() : null);
