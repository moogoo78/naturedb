import { writable, readable, derived, get } from 'svelte/store';
import { fetchData } from './utils.js';

export const HOST = readable(import.meta.env.VITE_HOST_URL);

const reArray = /^\/admin\/collections\/(\d+)\/records\/(\d+)/.exec(document.location.pathname);
const reArray2 = /^\/admin\/collections\/(\d+)/.exec(document.location.pathname);

export const COLLECTION_ID = readable((reArray) ? reArray[1] : reArray2[1]);
export const RECORD_ID = readable((reArray) ? reArray[2] : null);

const getOptions = async () => {
  let url = `${get(HOST)}/api/v1/admin/collections/${get(COLLECTION_ID)}/options`;
  return await fetchData(url);
};

let result = await getOptions();
let aTypeRocord = [];
let aTypeUnit = [];

const getValues = async () => {
  let url = `${get(HOST)}/api/v1/admin/records/${get(RECORD_ID)}`;
  return await fetchData(url);
};

let ret = {
  ...result,
  project_list: result.project_list,
  collector_list: result.person_list.filter( (x) => (x.is_collector) ? true : false),
  identifier_list: result.person_list.filter( (x) => (x.is_identifier) ? true : false),
};
delete result.person_list;
export const allOptions = readable(ret);
export const values = readable((reArray) ? await getValues() : null);
