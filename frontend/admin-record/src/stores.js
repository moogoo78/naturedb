import { writable, readable, derived, get } from 'svelte/store';
import { fetchData } from './utils.js';

export const HOST = readable(import.meta.env.VITE_HOST_URL);
export const RECORD_ID = readable(100); // TODO get values here

const getOptions = async () => {
  //console.log(location.pathname)
  let collectionId = 1; // TODO
  let url = `${get(HOST)}/api/v1/admin/collections/${collectionId}/options`;
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
export const values = readable(await getValues());
