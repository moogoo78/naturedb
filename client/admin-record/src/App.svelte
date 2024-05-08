<script>
  import { onMount } from 'svelte';
  import { HOST, RECORD_ID, COLLECTION_ID, allOptions, values, hasError } from './stores.js';
  import Select2a from './lib/Select2a.svelte'
  import FormWidget from './lib/FormWidget.svelte';
  import AttributeBox from './lib/AttributeBox.svelte';

  import { fetchData, filterItems, convertDDToDMS, convertDMSToDD } from './utils.js';

  let formValues = {};
  let fetchOptions = {
    identificationTaxon: [],
    namedAreaFree: [],
    namedAreas: {
      COUNTRY: [],
      ADM1: [],
      ADM2: [],
      ADM3: [],
    }
  };
  let fetchLoading = {
    identificationTaxon: [],
    namedAreaFree: false,
    namedAreas: {
      ADM1: false,
      ADM2: false,
      ADM3: false,
    }
  }

  let tmpCoordinates = {
    lonDD: null,
    latDD: null,
    lonDir: null,
    lonDeg: null,
    lonMin: null,
    lonSec: null,
    latDir: null,
    latDeg: null,
    latMin: null,
    latSec: null,
  };
  let hasNamedAreaAdmin3 = false;

  const syncCoordinates = (value, convertFrom) => {
    let v = parseFloat(value);
    switch (convertFrom) {
    case 'longitudeDecimal':
      if ((v >= 0 && v <= 180) || (v < 0 && v >= -180) ) {
        tmpCoordinates.lonDD.classList.remove('uk-form-danger')
        let dmsLongitude = convertDDToDMS(v)
        tmpCoordinates.lonDir.value = dmsLongitude[0];
        tmpCoordinates.lonDeg.value = dmsLongitude[1];
        tmpCoordinates.lonMin.value = dmsLongitude[2]
        tmpCoordinates.lonSec.value = dmsLongitude[3]
      } else {
        tmpCoordinates.lonDD.classList.add('uk-form-danger')
      }
      break;
    case 'latitudeDecimal':
      if ((v >= 0 && v <= 90) || (v < 0 && v >= -90) ) {
        tmpCoordinates.latDD.classList.remove('uk-form-danger')
        let dmsLatitude = convertDDToDMS(v)
        tmpCoordinates.latDir.value = dmsLatitude[0]
        tmpCoordinates.latDeg.value = dmsLatitude[1]
        tmpCoordinates.latMin.value = dmsLatitude[2]
        tmpCoordinates.latSec.value = dmsLatitude[3]
      } else {
        tmpCoordinates.latDD.classList.add('uk-form-danger')
      }
      break;
    case 'longitudeDMS':
      let d = Math.abs(tmpCoordinates.lonDeg.value);
      let m = Math.abs(tmpCoordinates.lonMin.value);
      let s = Math.abs(tmpCoordinates.lonSec.value);

      if (d >= 0 && d <= 180) {
        tmpCoordinates.lonDeg.classList.remove('uk-form-danger');
        if (m >= 0 && m <= 60) {
          const DMSList = [
            tmpCoordinates.lonDir.value,
            d,
            m,
            s
          ];
          tmpCoordinates.lonDD.value = convertDMSToDD(DMSList);
          tmpCoordinates.lonMin.classList.remove('uk-form-danger');
        } else {
          tmpCoordinates.lonMin.classList.add('uk-form-danger');
        }
      } else {
        tmpCoordinates.lonDeg.classList.add('uk-form-danger');
      }
      break;
    case 'latitudeDMS':
      let d2 = Math.abs(tmpCoordinates.latDeg.value);
      let m2 = Math.abs(tmpCoordinates.latMin.value);
      let s2 = Math.abs(tmpCoordinates.latSec.value);
      if (d2 >= 0 && d2 <= 90) {
        tmpCoordinates.latDeg.classList.remove('uk-form-danger');
        if (m2 >= 0 && m2 <= 60) {
          const DMSList = [
            tmpCoordinates.latDir.value,
            d2,
            m2,
            s2
          ];
          //console.log(DMSList, convertDMSToDD(DMSList));
          tmpCoordinates.latDD.value = convertDMSToDD(DMSList);
          tmpCoordinates.latMin.classList.remove('uk-form-danger');
        } else {
          tmpCoordinates.latMin.classList.add('uk-form-danger');
        }
      } else {
        tmpCoordinates.lonDeg.classList.add('uk-form-danger');
      }
    }
  };

  onMount(async () => {
    //console.log('mount');
    if (formValues.longitude_decimal) {
      syncCoordinates(formValues.longitude_decimal, 'longitudeDecimal');
    }
    if (formValues.latitude_decimal) {
      syncCoordinates(formValues.latitude_decimal, 'latitudeDecimal');
    }
  });

  const init = async () => {
    // apply data
    formValues.project = $values.project;
    formValues.field_number = $values.field_number;
    formValues.collect_date = $values.collect_date;
    formValues.collect_date_text = $values.collect_date_text;
    formValues.verbatim_collector = $values.verbatim_collector;
    formValues.companion_text = $values.companion_text;
    formValues.companion_text_en = $values.companion_text_en;
    formValues.field_note = $values.field_note;
    formValues.field_note_en = $values.field_note_en;
    formValues.longitude_decimal = $values.longitude_decimal;
    formValues.latitude_decimal = $values.latitude_decimal;
    formValues.verbatim_latitude = $values.verbatim_latitude;
    formValues.verbatim_longitude = $values.verbatim_longitude;
    formValues.verbatim_locality = $values.verbatim_locality;
    formValues.locality_text = $values.locality_text;
    formValues.locality_text_en = $values.locality_text_en;
    formValues.altitude = $values.altitude;
    formValues.altitude2 = $values.altitude2;
    formValues.collector = {
      text: $values.collector.display_name,
      value: $values.collector.id
    };
    formValues.assertions = {};
    for (const [name, value] of Object.entries($values.assertions)) {
      formValues.assertions[name] = {text: value, value: value};
    }
    formValues.identifications = $values.identifications.map( (item) => {
      fetchOptions.identificationTaxon.push([]);
      fetchLoading.identificationTaxon.push(false);
      let tmp = {...item};
      if (item.identifier) {
        tmp.identifier = {
          text: tmp.identifier.display_name,
          value: tmp.identifier.id,
        }
      }
      if (item.taxon) {
        tmp.taxon = {
          text: tmp.taxon.display_name,
          value: tmp.taxon.id,
        }
      }
      return tmp;
    });
    formValues.units = [...$values.units];

    // unit-assertions data struc
    formValues.units = $values.units.map( (unit) => {
      let attrs = {};
      $allOptions.assertion_type_unit_list.forEach( atype => {
        attrs[atype.name] = '';
        if (atype.name in unit.assertions) {
          let value = unit.assertions[atype.name].value;
          if (atype.input_type === 'select') {
            attrs[atype.name] = {text: unit.assevalue, value: value};
          } else {
            attrs[atype.name] = value;
          }
        }
      });
      return {
        ...unit,
        assertions: attrs,
      }
    })
    formValues.named_areas = {};
    //formValues.named_areas__admin = $values.named_areas__admin;
    // TODO
    let tmp_admin = [];
    for(const [name, data] of Object.entries($values.named_areas)) {
      formValues.named_areas[name] = {
        text: data.display_name,
        value: data.id,
      };
      //if ([1, 7, 8, 9].indexOf(data.area_class_id) >= 0) { // TODO
      //  tmp_admin.push(`${data.area_class_id}_${data.display_name}`);
      //}
    }
    //if (tmp_admin.length > 0) {
      //displayNamedAreasAdmin = tmp_admin.sort().map( x => x.substring(2)).join(', ');
    //}
  }; // end of init

  if ($values) {
    init();
  } else if ($hasError) {
      alert($hasError);
  } else {
    formValues.assertions = {};
    formValues.units = [];
    formValues.identifications = [];
    formValues.named_areas = [];
  }

  console.log($allOptions, $values, formValues);

  const handleNamedAreaFreeInput = async (input) => {
    if (input) {
      if (input.slice(0, 1) === '台') {
        input = input.replace('台', '臺');
      }
      fetchLoading.namedAreaFree = true;
      let url = `${$HOST}/api/v1/named-areas?filter={"q":"${input}","area_class_id":[7,8,9]}`;
      let results = await fetchData(url);
      let options = results.data;
      fetchOptions = {
        ...fetchOptions,
        namedAreaFree: options
      };
      fetchLoading.namedAreaFree = false;
    }
  }
  const handleNamedAreaFreeSelect = async (selected) => {
    formValues.named_areas__admin = selected;
    formValues.named_areas__via = 'C';
    let url = `${$HOST}/api/v1/named-areas/${selected.value}?parents=1`;
    let result = await fetchData(url);
    result.higher_area_classes.forEach( x => {
      formValues.named_areas[x.area_class_name] = {
        text: x.display_text,
        value: x.id,
      }
    });
    formValues.named_areas[result.area_class.name] = selected;

    if (hasNamedAreaAdmin3) {
      formValues.named_areas.ADM3 = null;
    }
  }
  const handleNamedAreaAdminClear = (key) => {
    formValues.named_areas[key] = null;
    if (key === 'COUNTRY') {
      formValues.named_areas.ADM1 = null;
      formValues.named_areas.ADM2 = null;
      formValues.named_areas.ADM3 = null;
    } else if (key === 'ADM1') {
      formValues.named_areas.ADM2 = null;
      formValues.named_areas.ADM3 = null;
    } else if (hasNamedAreaAdmin3 && key === 'ADM2') {
      fetchLoading.namedAreas.ADM3 = true;
    }
  }

  const handleNamedAreaAdminSelect = async (selected, key) => {
    formValues.named_areas[key] = selected;
    formValues.named_areas__via = 'C';

    let url = `${$HOST}/api/v1/named-areas/?filter={"parent_id":${selected.value}}`;

    if (key === 'COUNTRY') {
      fetchLoading.namedAreas.ADM1 = true;
    } else if (key === 'ADM1') {
      fetchLoading.namedAreas.ADM2 = true;
    } else if (hasNamedAreaAdmin3 && key === 'ADM2') {
      fetchLoading.namedAreas.ADM3 = true;
    }

    let results = await fetchData(url);

    if (key === 'COUNTRY') {
      fetchOptions.namedAreas.ADM1 = results.data;
      fetchLoading.namedAreas.ADM1 = false;
      formValues.named_areas.ADM1 = null;
      formValues.named_areas.ADM2 = null;
      formValues.named_areas.ADM3 = null;
    } else if (key === 'ADM1') {
      fetchOptions.namedAreas.ADM2 = results.data;
      fetchLoading.namedAreas.ADM2 = false;
      formValues.named_areas.ADM2 = null;
      formValues.named_areas.ADM3 = null;
    } else if (hasNamedAreaAdmin3 && key === 'ADM2') {
      fetchOptions.namedAreas.ADM3 = results.data;
      fetchLoading.namedAreas.ADM3 = false;
      formValues.named_areas.ADM3 = null;
    }
  }

  const handleNamedAreaAdminLonLat = async () => {
    const lon = tmpCoordinates.lonDD;
    const lat = tmpCoordinates.latDD;
    if (lon && lon.value && lat && lat.value) {
      const ft = JSON.stringify({
        within: {
          srid: 4326,
          point: [lon.value, lat.value],
        },
        area_class_id: [7, 8, 9]
      });
      let result = await fetchData(`${$HOST}/api/v1/named-areas?filter=${ft}`);
      if (result.total > 0) {
        let x = result.data[result.data.length-1];
        formValues.named_areas__admin = {text: x.display_name, value: x.id};
        formValues.named_areas__via = 'B';
        result.data.forEach( x => {
          formValues.named_areas[x.area_class.name] = {
            text: x.display_name,
            value: x.id,
          }
        });
      }
    }
  }

  const onIdentificationTaxonInput = async (input, index) => {
    if (input) {
      fetchLoading.identificationTaxon[index] = true;
      let url = `${$HOST}/api/v1/taxa?filter={"q":"${input}"}`;
      let results = await fetchData(url);
      let options = results.data;
      let tmp = [...fetchOptions.identificationTaxon];
      tmp[index] = options.map( (x) => ({text: x.display_name, value: x.id}));
      fetchOptions = {
        ...fetchOptions,
        identificationTaxon: tmp
      };
      fetchLoading.identificationTaxon[index] = false;
    }
  }

  const onSubmit = (isClose=false) => {
    //console.log(formValues);

    let url = ($RECORD_ID) ? `${$HOST}/api/v1/admin/collections/${$COLLECTION_ID}/records/${$RECORD_ID}` : `${$HOST}/api/v1/admin/collections/${$COLLECTION_ID}/records`;

    fetch(url, {
      method: "POST",
      //mode: "cors", // no-cors, *cors, same-origin
      cache: "no-cache", // *default, no-cache, reload, force-cache, only-if-cached
      credentials: "same-origin", // include, *same-origin, omit
      headers: {
        "Content-Type": "application/json",
        // 'Content-Type': 'application/x-www-form-urlencoded',
      },
      redirect: "follow", // manual, *follow, error
      referrerPolicy: "no-referrer", // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
      body: JSON.stringify(formValues), // body data type must match "Content-Type" header
    })
      .then(response => response.json())
      .then(result => {
        console.log(result);
        if ($RECORD_ID) {
        } else {

        }
        if (isClose === true) {
          location.replace(`${$HOST}/admin/records`)
        } else {
          UIkit.notification('已儲存', {timeout: 5000});
        }

        if (result.next) {
          location.replace(result.next)
        }
      });
  };

  const removeUnit = (index) => {
    let yes = confirm('確定刪除嗎？');
    if (yes) {
      let tmp =[...formValues.units];
      tmp.splice(index, 1);
      formValues.units = tmp;
    }
  }

  const removeIdentification = (index) => {
    let yes = confirm('確定刪除嗎？');
    if (yes) {
      let tmp =[...formValues.identifications];
      tmp.splice(index, 1);
      formValues.identifications = tmp;
    }
  }

  const addIdentification = () => {
    let seq = formValues.identifications.length + 1;
    formValues.identifications = [...formValues.identifications, {sequence: seq}];
    fetchOptions.identificationTaxon.push([]);
    fetchLoading.identificationTaxon.push(false);
  }

  const syncLongitudeDecimal = (e) => {
    const d = Math.abs(converterLongitudeDegree.value)
    const m = converterLongitudeMinute.value

    if (d >= 0 && d <= 180) {
      converterLongitudeDegree.classList.remove('uk-form-danger')
      if (m >= 0 && m <= 90) {
        const DMSList = [
          converterLongitudeDirection.value,
          converterLongitudeDegree.value,
          converterLongitudeMinute.value,
          converterLongitudeSecond.value,
        ]
        longitudeDecimal.value = convertDMSToDD(DMSList)
        converterLongitudeMinute.classList.remove('uk-form-danger')
      } else {
        converterLongitudeMinute.classList.add('uk-form-danger')
      }
    } else {
      converterLongitudeDegree.classList.add('uk-form-danger')
    }
  }

  // HACK, taiwan and china has adm3
  $: if (formValues.named_areas.COUNTRY
         && [1311, 1358].indexOf(formValues.named_areas.COUNTRY.value) >= 0) {
    hasNamedAreaAdmin3 = true;
  } else {
    hasNamedAreaAdmin3 = false;
  }
  const getDisplayNamedAreaAdmin = (namedAreas) => {
    let naList = [];
    for (let key of ['COUNTRY', 'ADM1', 'ADM2', 'ADM3']) {
      if (key in namedAreas && namedAreas[key]?.value) {
        naList.push(namedAreas[key].text);
      }
    }
    return naList.join(' ,');
  };
  $: displayNamedAreaAdmin = getDisplayNamedAreaAdmin(formValues.named_areas);

</script>

<main>
  <nav aria-label="Breadcrumb">
    <ul class="uk-breadcrumb">
      <li><a href="/admin">admin</a></li>
      <li><a href="/admin/records">採集記錄</a></li>
      {#if $RECORD_ID}
        <li><span aria-current="page">{$RECORD_ID}</span></li>
      {/if}
    </ul>
  </nav>
  <form id="record-form" class="uk-form-stacked">
  <p>Collection: <span class="uk-label uk-label-warning">{$allOptions.collection.label}</span></p>
  </form>

  <form class="uk-grid-collapse uk-child-width-1-2" uk-grid>
    <div>

    </div>
    <div>
      <button class="uk-button uk-button-primary" type="submit" on:click|preventDefault={() => onSubmit(true)}>儲存並關閉</button>
      <button class="uk-button uk-button-default" type="submit" on:click|preventDefault={() => onSubmit(false)}>儲存並繼續編輯</button>
    </div>
    <div><!-- left side -->
      <div class="uk-child-width-expand uk-grid-collapse mg-form-part" uk-grid>
        <fieldset>
          <legend>採集資訊</legend>
          <div class="uk-width-1-1 uk-grid-collapse" uk-grid>
            <div class="uk-width-2-3">
              <FormWidget>
                <svelte:fragment slot="label">
                  <label class="uk-width-auto" for="form-collector">採集者</label>
                </svelte:fragment>
                <svelte:fragment slot="control">
                  <Select2a
                    options={$allOptions.collector_list.map( x => ({text: x.display_name, value: x.id}))}
                    value={formValues.collector}
                    onSelect={(selected)=>{
                      formValues.collector = selected;
                    }}
                    onClear={()=>{formValues.collector=null;}}
                    />
                </svelte:fragment>
              </FormWidget>
            </div>
            <div class="uk-width-1-3">
              <FormWidget id="form-field-number" label="採集號" type="input-text" bind:value={formValues.field_number} />
            </div>
          </div>
          <div class="uk-child-width-1-3 uk-grid-collapse" uk-grid>
            <div>
              <FormWidget id="form-date-text" label="採集者(verbatim)" type="input-text" placeholder="" bind:value={formValues.verbatim_collector}/>
            </div>
            <div>
              <FormWidget id="form-date" label="採集日期" type="input-date" bind:value={formValues.collect_date} />
            </div>
            <div>
              <FormWidget id="form-date-text" label="採集日期(verbatim)" type="input-text" placeholder="1990 or 1992-03" bind:value={formValues.collect_date_text}/>
            </div>
          </div>
          <div class="uk-child-width-1-2 uk-grid-collapse" uk-grid>
            <div>
              <FormWidget id="form-companion" label="隨同人員" type="textarea" bind:value={formValues.companion_text} />
            </div>
            <div>
              <FormWidget id="form-companion_en" label="隨同人員(英文)" type="textarea" bind:value={formValues.companion_text_en} />
            </div>
          </div>
          <div class="uk-child-width-1-2 uk-grid-collapse" uk-grid>
            <div>
              <FormWidget id="form-companion" label="採集記錄" type="textarea" bind:value={formValues.field_note} />
            </div>
            <div>
              <FormWidget id="form-companion_en" label="採集記錄(英文)" type="textarea" bind:value={formValues.field_note_en} />
            </div>
          </div>
          <div class="uk-width-1-1 uk-grid-small" uk-grid>
            <h4 class="uk-heading-bullet">地點資訊</h4>
          </div>
          <div class="uk-width-1-1 uk-grid-small" uk-grid>
            <h5 class="uk-heading-bullet">坐標系統</h5>
          </div>
          <div class="uk-width-1-1 uk-grid-collapse" uk-grid>
            <div class="uk-width-1-2">
              <FormWidget id="form-datum" label="大地基準(geodetic datum)" type="select" bind:value={formValues.geodetic_datum} options={[{text: 'WGS84', value: 'WGS84'}, {text: 'TWD97', value: 'TWD97'},{text: 'TWD67', value: 'TWD67'}]}/>
            </div>
            <div class="uk-width-1-4">
              <FormWidget id="form-altitude" label="海拔" type="input-text" bind:value={formValues.altitude} />
            </div>
            <div class="uk-width-1-4">
              <FormWidget id="form-altitude2" label="海拔2" type="input-text" bind:value={formValues.altitude2}/>
            </div>
            <div class="uk-width-1-2">
              <FormWidget id="form-lon-decimal" label="Verbatim 經度" type="input-text" bind:value={formValues.verbatim_longitude} />
            </div>
            <div class="uk-width-1-2">
              <FormWidget id="form-lat-decimal" label="Verbatim 緯度" type="input-text" bind:value={formValues.verbatim_latitude}/>
            </div>
          </div>
          <div class="uk-width-1-1 uk-grid-collapse" uk-grid>
            <div class="uk-width-1-2">
              <FormWidget>
                <svelte:fragment slot="label">
                  <label class="uk-width-auto" for="form-lon-decimal">經度(十進位)</label>
                </svelte:fragment>
                <svelte:fragment slot="control">
                  <input type="text" id="form-lon-decimal" class="uk-input uk-form-small" on:input={(e) => syncCoordinates(e.target.value, 'longitudeDecimal')} bind:this={tmpCoordinates.lonDD} bind:value={formValues.longitude_decimal} />
                  <div class="uk-comment-meta">+/-180</div>
                </svelte:fragment>
              </FormWidget>
            </div>
            <div class="uk-width-1-2">
              <FormWidget>
                <svelte:fragment slot="label">
                  <label class="uk-width-auto" for="form-lon-decimal">緯度(十進位)</label>
                </svelte:fragment>
                <svelte:fragment slot="control">
                  <input type="text" id="form-lat-decimal" class="uk-input uk-form-small" on:input={(e) => syncCoordinates(e.target.value, 'latitudeDecimal')} bind:this={tmpCoordinates.latDD} bind:value={formValues.latitude_decimal} />
                  <div class="uk-comment-meta">+/-90</div>
                </svelte:fragment>
              </FormWidget>
            </div>

            <div class="uk-width-1-1">
              <div class="uk-flex">
                  <div>
                    <FormWidget>
                      <svelte:fragment slot="label">
                        <label class="uk-width-auto" for="converter-longitude-direction">經度(60進位)</label>
                      </svelte:fragment>
                      <svelte:fragment slot="control">
                        <select class="uk-select uk-form-small mg-input-xsmall" id="converter-longitude-direction" on:input={(e) => syncCoordinates(e.target.value, 'longitudeDMS')} bind:this={tmpCoordinates.lonDir}>
                          <option value="">-- 選擇--</option>
                          <option value="1">東經</option>
                          <option value="-1">西經</option>
                        </select>
                      </svelte:fragment>
                    </FormWidget>
                  </div>
                  <div>
                    <FormWidget>
                      <svelte:fragment slot="label2">
                        <label class="uk-width-auto" for="converter-longitude-degree">度</label>
                      </svelte:fragment>
                      <svelte:fragment slot="control">
                        <input class="uk-input uk-form-small mg-input-xsmall" type="text" id="converter-longitude-degree" on:input={(e) => syncCoordinates(e.target.value, 'longitudeDMS')} bind:this={tmpCoordinates.lonDeg}/>
                        <div class="uk-comment-meta">0-60°</div>
                      </svelte:fragment>
                    </FormWidget>
                  </div>
                  <div>
                    <FormWidget>
                      <svelte:fragment slot="label2">
                        <label class="uk-width-auto" for="converter-longitude-minute">分</label>
                      </svelte:fragment>
                      <svelte:fragment slot="control">
                        <input class="uk-input uk-form-small mg-input-xsmall" type="text" id="converter-longitude-minute" on:input={(e) => syncCoordinates(e.target.value, 'longitudeDMS')} bind:this={tmpCoordinates.lonMin}/>
                        <div class="uk-comment-meta">0-60'</div>
                      </svelte:fragment>
                    </FormWidget>
                  </div>
                  <div>
                    <FormWidget>
                      <svelte:fragment slot="label2">
                        <label class="uk-width-auto" for="converter-longitude-second">秒</label>
                      </svelte:fragment>
                      <svelte:fragment slot="control">
                        <input class="uk-input uk-form-small mg-input-xsmall" type="text" id="converter-longitude-second" on:input={(e) => syncCoordinates(e.target.value, 'longitudeDMS')}  bind:this={tmpCoordinates.lonSec} />
                        <div class="uk-comment-meta">0-60"</div>
                      </svelte:fragment>
                    </FormWidget>
                  </div>
                </div>
                <div class="uk-flex">
                  <div>
                    <FormWidget>
                      <svelte:fragment slot="label">
                        <label class="uk-width-auto" for="converter-latitude-degree">緯度(60進位)</label>
                      </svelte:fragment>
                      <svelte:fragment slot="control">
                        <select class="uk-select uk-form-small mg-input-xsmall" id="converter-latitude-direction" on:change={(e) => syncCoordinates(e.target.value, 'latitudeDMS')} bind:this={tmpCoordinates.latDir}>
                          <option value="">-- 選擇--</option>
                          <option value="1">北緯</option>
                          <option value="-1">南緯</option>
                        </select>
                      </svelte:fragment>
                    </FormWidget>
                  </div>
                  <div>
                    <FormWidget>
                      <svelte:fragment slot="label2">
                        <label class="uk-width-auto" for="converter-altitude-degree">度</label>
                      </svelte:fragment>
                      <svelte:fragment slot="control">
                        <input class="uk-input uk-form-small mg-input-xsmall" type="text" id="converter-altitude-degree" on:input={(e) => syncCoordinates(e.target.value, 'latitudeDMS')} bind:this={tmpCoordinates.latDeg} />
                        <div class="uk-comment-meta">0-60°</div>
                      </svelte:fragment>
                    </FormWidget>
                  </div>
                  <div>
                    <FormWidget>
                      <svelte:fragment slot="label2">
                        <label class="uk-width-auto" for="converter-altitude-minute">分</label>
                      </svelte:fragment>
                      <svelte:fragment slot="control">
                        <input class="uk-input uk-form-small mg-input-xsmall" type="text" id="converter-altitude-minute" on:input={(e) => syncCoordinates(e.target.value, 'latitudeDMS')} bind:this={tmpCoordinates.latMin} />
                        <div class="uk-comment-meta">0-60'</div>
                      </svelte:fragment>
                    </FormWidget>
                  </div>
                  <div>
                    <FormWidget>
                      <svelte:fragment slot="label2">
                        <label class="uk-width-auto" for="converter-altitude-second">秒</label>
                      </svelte:fragment>
                      <svelte:fragment slot="control">
                        <input class="uk-input uk-form-small mg-input-xsmall" type="text" id="converter-altitude-second" on:input={(e) => syncCoordinates(e.target.value, 'latitudeDMS')} bind:this={tmpCoordinates.latSec} />
                        <div class="uk-comment-meta">0-60"</div>
                      </svelte:fragment>
                    </FormWidget>
                  </div>
                </div>
            </div>
          </div>
          <div class="uk-width-1-1 uk-grid-small" uk-grid>
            <h4 class="uk-heading-bullet">地點名稱</h4>
          </div>
          <div class="uk-width-1-1">
            <div uk-grid>
              <div class="uk-width-auto">
                <ul class="uk-tab-left" uk-tab="connect: #component-tab-left;">
                  <li><a href="#">行政區選單</a></li>
                  <li><a href="#">關鍵字查詢</a></li>
                  <li><a href="#">從經緯度取得</a></li>
                </ul>
              </div>
              <div class="uk-width-expand">
                <ul id="component-tab-left" class="uk-switcher">
                  <li>
                    <div class="uk-grid-collapse" uk-grid>
                      <div class="uk-width-1-1">
                        <FormWidget>
                          <svelte:fragment slot="label">
                            <label class="uk-width-auto" for="form-named-area__country">國家</label>
                          </svelte:fragment>
                          <svelte:fragment slot="control">
                            <Select2a
                              options={$allOptions.named_areas.country.options.map( x => ({text: x.display_name, value: x.id}))}
                              onSelect={(x) => handleNamedAreaAdminSelect(x, 'COUNTRY')}
                              value={formValues.named_areas.COUNTRY}
                              onClear={() => {handleNamedAreaAdminClear('COUNTRY')}}
                              />
                          </svelte:fragment>
                        </FormWidget>
                      </div>
                      <div class="uk-width-1-1">
                        <FormWidget>
                          <svelte:fragment slot="label">
                            <label class="uk-width-auto" for="form-named-area-adm1">1級行政區</label>
                          </svelte:fragment>
                          <svelte:fragment slot="control">
                            {#if fetchLoading.namedAreas.ADM1 === true}
                              <div uk-spinner></div>
                            {/if}
                            <Select2a
                              options={fetchOptions.namedAreas.ADM1.map( x => ({text: x.display_name, value: x.id}) )}
                              onSelect={(x) => handleNamedAreaAdminSelect(x, 'ADM1')}
                              value={formValues.named_areas.ADM1}
                              onClear={() => {handleNamedAreaAdminClear('ADM1')}}
                              />
                          </svelte:fragment>
                        </FormWidget>
                      </div>
                      <div class="uk-width-1-1">
                        <FormWidget>
                          <svelte:fragment slot="label">
                            <label class="uk-width-auto" for="form-named-area-adm2">2級行政區</label>
                          </svelte:fragment>
                          <svelte:fragment slot="control">
                            {#if fetchLoading.namedAreas.ADM2 === true}
                              <div uk-spinner></div>
                            {/if}
                            <Select2a
                              options={fetchOptions.namedAreas.ADM2.map( x=> ({text: x.display_name, value: x.id}))}
                              onSelect={(x) => {handleNamedAreaAdminSelect(x, 'ADM2')}}
                              value={formValues.named_areas.ADM2}
                              onClear={() => {handleNamedAreaAdminClear('ADM2')}}
                              />
                          </svelte:fragment>
                        </FormWidget>
                      </div>
                      {#if hasNamedAreaAdmin3}
                      <div class="uk-width-1-1">
                        <FormWidget>
                          <svelte:fragment slot="label">
                            <label class="uk-width-auto" for="form-named-area-adm3">3級行政區</label>
                          </svelte:fragment>
                          <svelte:fragment slot="control">
                            {#if fetchLoading.namedAreas.ADM3 === true}
                              <div uk-spinner></div>
                            {/if}
                            <Select2a
                              options={fetchOptions.namedAreas.ADM3.map( x=> ({text: x.display_name, value: x.id}))}
                              onSelect={(x) => {handleNamedAreaAdminSelect(x, 'ADM3')}}
                              value={formValues.named_areas.ADM3}
                              onClear={ () => {formValues.named_areas.ADM3 = null;}}
                              />
                          </svelte:fragment>
                        </FormWidget>
                      </div>
                      {/if}
                    </div>
                  </li>
                  <li>
                    <FormWidget>
                      <svelte:fragment slot="label">
                        <label class="uk-width-auto" for="form-named-area">行政區名稱</label>
                      </svelte:fragment>
                      <svelte:fragment slot="control">
                        {#if fetchLoading.namedAreaFree === true}
                          <div uk-spinner></div>
                        {/if}
                        <Select2a
                          options={fetchOptions.namedAreaFree.map((x) => ({text: x.display_name, value: x.id}))}
                          onSelect={handleNamedAreaFreeSelect}
                          value={formValues.named_areas__free}
                          onInput={handleNamedAreaFreeInput}
                          onClear={() => {
                            formValues.named_areas.COUNTRY = null;
                            formValues.named_areas.ADM1 = null;
                            formValues.named_areas.ADM2 = null;
                            formValues.named_areas.ADM3 = null;
                          }}
                          />
                      </svelte:fragment>
                    </FormWidget>
                  </li>
                  <li>
                    <button class="uk-button uk-button-primary" on:click|preventDefault={handleNamedAreaAdminLonLat}>從經緯度取得</button>
                  </li>
                </ul>
              </div>
            </div>
          </div>
          <div class="uk-width-1-1 mg-background-label">
            <FormWidget>
              <svelte:fragment slot="label">
                <label class="uk-width-auto">行政區名稱</label>
              </svelte:fragment>
              <svelte:fragment slot="control">
                <textarea class="uk-textarea" bind:value={displayNamedAreaAdmin} disabled rows="1"/>
              </svelte:fragment>
            </FormWidget>
          </div>
          {#each Object.entries($allOptions.named_areas) as [name, data]}
            <div class="uk-width-1-1">
              <FormWidget>
                <svelte:fragment slot="label">
                  <label class="uk-width-auto">{data.label}</label>
                </svelte:fragment>
                <svelte:fragment slot="control">
                  <Select2a
                    options={data.options.map((x) => ({text: x.display_name, value: x.id}))}
                    value={formValues.named_areas[name]}
                    onSelect={(selected)=>{
                      formValues.named_areas[name] = selected;
                    }}
                    onClear={()=>{formValues.named_areas[name] = null;}}
                    />
                </svelte:fragment>
              </FormWidget>
            </div>
          {/each}
          <div class="uk-width-1-1 uk-grid-collapse" uk-grid>
            <div class="uk-width-1-2">
              <FormWidget id="form-locality_text" label="詳細地點" type="textarea" bind:value={formValues.locality_text} />
            </div>
            <div class="uk-width-1-2">
              <FormWidget id="form-locality_text_en" label="詳細地點(英文)" type="textarea" bind:value={formValues.locality_text_en} />
            </div>
            <div class="uk-width-1-1">
              <FormWidget id="form-locality_text" label="地點(Verbatim)" type="textarea" bind:value={formValues.verbatim_locality} />
            </div>
          </div>
        </fieldset>
      </div>
      <div class="uk-child-width-1-1- uk-grid-collapse mg-form-part" uk-grid>
        <!-- <button class="uk-button uk-button-default" type="button" uk-toggle="target: .toggle">Toggle</button> -->
        <div class="toggle">
          <fieldset>
            <legend>棲地環境</legend>
            <div class="uk-child-width-1-1 uk-grid-small" uk-grid>
              {#each $allOptions.assertion_type_record_list as data}
                <FormWidget>
                  <svelte:fragment slot="label">
                    <label class="uk-width-auto" for="form-named-area">{data.label}</label>
                  </svelte:fragment>
                  <svelte:fragment slot="control">
                  <Select2a
                    options={data.options.map( x => ({text: x.display_name, value: x.value}))}
                    value={formValues.assertions[data.name]}
                    onSelect={(selected)=>{
                      formValues.assertions[data.name] = selected;
                    }}
                    onClear={()=>{formValues.assertions[data.name]=null;}}
                    />
                  </svelte:fragment>
                </FormWidget>
              {/each}
            </div>
          </fieldset>
        </div>
      </div>
    </div>
    <div><!-- right side -->
      <div class="uk-child-width-expand uk-grid-collapse mg-form-part" uk-grid>
        <fieldset>
          <legend>資料</legend>
          <div class="uk-child-width-1-1 uk-grid-collapse" uk-grid>
            <div class="uk-width-1-1">
              <FormWidget id="form-project" label="計劃" type="select" bind:value={formValues.project} options={$allOptions.project_list.map((x) => ({text: x.name, value: x.id}))} />
            </div>
            <!-- <div class="uk-width-1-4"> -->
            <!--   <input type="text" class="uk-input uk-form-small" disabled value={$allOptions.current_user}/> -->
            <!-- </div> -->
          </div>
        </fieldset>
      </div>
      <div class="uk-child-width-expand uk-grid-collapse mg-form-part" uk-grid>
        <fieldset>
          <legend>鑑定</legend>
          <button class="uk-button uk-button-small uk-button-primary" on:click|preventDefault={addIdentification}>新增</button>
          <div class="uk-child-width-1-1 uk-grid-collapse" uk-grid>
            {#each formValues.identifications as idObj, idx}
              <div class="uk-grid-collapse mg-iden-box" uk-grid>
                <div class="uk-width-1-6">
                  <input class="uk-input uk-form-small mg-input-xsmall" bind:value={idObj.sequence} type="number"/>
                </div>
                <div class="uk-width-5-6">
                  <FormWidget>
                    <svelte:fragment slot="label">
                      <label class="uk-width-auto">學名</label>
                    </svelte:fragment>
                    <svelte:fragment slot="control">
                      <Select2a
                        options={fetchOptions.identificationTaxon[idx]}
                        onSelect={(selected) => {
                          idObj.taxon = selected;
                        }}
                        value={idObj.taxon}
                        onInput={(input) => onIdentificationTaxonInput(input, idx)}
                        />
                    </svelte:fragment>
                  </FormWidget>
                </div>
                <div class="uk-width-2-3">
                  <FormWidget>
                    <svelte:fragment slot="label">
                      <label class="uk-width-auto">鑒定者</label>
                    </svelte:fragment>
                    <svelte:fragment slot="control">
                      <Select2a
                        options={$allOptions.identifier_list.map( x => ({text: x.display_name, value: x.id}))}
                        onSelect={(selected) => {
                          idObj.identifier = selected;
                        }}
                        value={idObj.identifier}
                        onClear={()=>{idObj.identifier=null;}}
                        />
                    </svelte:fragment>
                  </FormWidget>
                </div>
                <div class="uk-width-1-3">
                  <FormWidget id={`form-iden-${idx}-date`} bind:value={idObj.date} label="鑒定日期" type="input-date"></FormWidget>
                </div>
                <div class="uk-width-1-3">
                  <FormWidget id={`form-iden-${idx}-date-text`} bind:value={idObj.date_text} label="鑒定日期(文字)" type="input-text"></FormWidget>
                </div>
                <div class="uk-width-1-3">
                </div>
                <div class="uk-width-1-3 uk-text-right">
                  <button type="button" class="uk-button uk-button-secondary uk-form-small" on:click|preventDefault={() => removeIdentification(idx)}>刪除</button>
                </div> 
              </div>
            {/each}
          </div>
        </fieldset>
      </div>
      <div class="uk-child-width-expand uk-grid-collapse mg-form-part" uk-grid>
        <fieldset>
          <legend>標本</legend>
          <button class="uk-button uk-button-small uk-button-primary" on:click|preventDefault={() => {
            formValues.units = [...formValues.units, {assertions:{}}];
            }}>新增</button>
          <div class="uk-child-width-1-1 uk-grid-collapse" uk-grid>
            <table class="uk-table uk-table-small uk-table-divider uk-table-striped">
              <thead>
                <tr>
                  <th class="uk-width-small">館號</th>
                  <th class="uk-width-small">複份號</th>
                  <th>部件類別</th>
                  <th>展開</th>
                </tr>
              </thead>
              <tbody>
                {#each formValues.units as unit, idx}
                <tr>
                  <td>
                    <input type="text" class="uk-input uk-form-small" bind:value={unit.accession_number} />
                  </td>
                  <td>
                    <input type="text" class="uk-input uk-form-small" bind:value={unit.duplication_number} />
                  </td>
                  <td>
                    <select class="uk-select uk-form-small" bind:value={unit.kind_of_unit}>
                      <option value=""></option>
                      {#each $allOptions.unit_kind_of_unit as item}
                        <option value={item[0]}>{item[1]}</option>
                      {/each}
                    </select>
                  </td>
                  <td>
                    <button uk-toggle="target: #{`unit-${unit.id}-extend`}" type="button" class="uk-button uk-form-small">展開</button>
                  </td>
                </tr>
                <tr id={`unit-${unit.id}-extend`} hidden>
                  <td colspan="7">
                    <div class="uk-width-1-1 uk-grid-collapse" uk-grid>
                      <div class="uk-width-1-1 uk-grid-small">
                        <h4 class="uk-heading-bullet">標本狀態</h4>
                      </div>
                      <div class="uk-width-1-1">
                        <FormWidget>
                          <svelte:fragment slot="label">
                            <label class="uk-width-auto" for={`form-${unit}-guid`}>GUID</label>
                          </svelte:fragment>
                          <svelte:fragment slot="control">
                            <span class="uk-text-warning">{unit.guid}</span>
                          </svelte:fragment>
                        </FormWidget>
                      </div>
                      <div class="uk-width-1-3">
                        <FormWidget id={`form-${unit.id}-dispos`} label="Disposition" type="select" bind:value={unit.disposotion} options={$allOptions.unit_disposition.map((x) => ({value: x[0], text: x[1]}))}/>
                      </div>
                      <div class="uk-width-1-3">
                        <FormWidget id={`form-${unit.id}-pub-status`} label="是否公開" type="select" bind:value={unit.pub_status} options={[{text:'是', value:'P'}, {text:'否', value:'N'}]} />
                      </div>
                      <div class="uk-width-1-1 uk-grid-small">
                        <h4 class="uk-heading-bullet">Preparation</h4>
                      </div>
                      <div class="uk-width-1-2">
                        <FormWidget id={`form-${unit.id}-p-type`} label="Preparation Type" type="select" bind:value={unit.preparation_type} options={$allOptions.unit_preparation_type.map((x) => ({value: x[0], text: x[1]}))}/>
                      </div>
                      <div class="uk-width-1-2">
                        <FormWidget id={`form-${unit.id}-p-date`} label="Preparation Date" type="input-date" bind:value={unit.preparation_date} />
                      </div>
                      <div class="uk-width-1-1 uk-grid-small">
                        <h4 class="uk-heading-bullet">標本取得</h4>
                      </div>
                      <div class="uk-width-1-2">
                        <FormWidget id={`form-${unit.id}-acq-type`} label="取得方式" type="select" bind:value={unit.acquisition_type} options={$allOptions.unit_acquisition_type.map((x) => ({value: x[0], text: x[1]}))}/>
                      </div>
                      <div class="uk-width-1-2">
                        <FormWidget id={`form-${unit.id}-acq-date`} label="取得日期" type="input-date" bind:value={unit.acquisition_date} />
                      </div>
                      <div class="uk-width-1-2">
                        <FormWidget>
                          <svelte:fragment slot="label">
                            <label class="uk-width-auto" for={`form-${unit}-acq-from`}>來源(人名)</label>
                          </svelte:fragment>
                          <svelte:fragment slot="control">
                            <Select2a
                              options={$allOptions.person_list.map( x => ({text: x.display_name, value: x.id}))}
                              value={unit.acquired_from}
                              onSelect={(selected)=>{ unit.acquired_from = selected;}}
                              onClear={()=>{unit.acquired_from = null;}}
                              />
                          </svelte:fragment>
                        </FormWidget>
                      </div>
                      <div class="uk-width-1-2">
                        <FormWidget id={`form-${unit.id}-acq-source_text`} label="來源(代號)" type="input-text" bind:value={unit.acquisition_source_text} />
                      </div>
                      <div class="uk-width-1-1 uk-grid-small">
                        <h4 class="uk-heading-bullet">模式標本</h4>
                      </div>
                      <div class="uk-width-1-3">
                        <FormWidget id={`form-${unit.id}-type-status`} label="Type Status" type="select" bind:value={unit.type_status} options={$allOptions.unit_type_status.map((x) => ({value: x[0], text: x[1]}))}/>
                      </div>
                      <div class="uk-width-1-3">
                        <FormWidget id={`form-${unit.id}-type-is-pub`} label="是否發表" type="select" bind:value={unit.type_is_published} options={[{text:'是', value:'Y'}, {text:'否', value:'N'}]} />
                      </div>
                      <div class="uk-width-1-1">
                        <FormWidget id={`form-${unit.id}-typified-name`} label="Typified Name" type="input-text" bind:value={unit.typified_name} />
                      </div>
                  <!--     <div class="uk-width-1-1"> -->
                  <!--       <FormWidget> -->
                  <!--         <svelte:fragment slot="label"> -->
                  <!--           <label class="uk-width-auto">綁定學名</label> -->
                  <!--         </svelte:fragment> -->
                  <!--         <svelte:fragment slot="control"> -->
                  <!--           <Select2a -->
                  <!--             options={fetchOptions.unitTypeTaxon[idx]} -->
                  <!--             onSelect={(selected) => { -->
                  <!--                unit.type_identification = selected; -->
                  <!--             }} -->
                  <!--       value={idObj.taxon} -->
                  <!--       onInput={(input) => onIdentificationTaxonInput(input, idx)} -->
                  <!--       /> -->
                  <!--   </svelte:fragment> -->
                  <!-- </FormWidget> -->
                      <div class="uk-width-1-1">
                        <FormWidget id={`form-${unit.id}-type-reference`} label="Reference" type="input-text" bind:value={unit.type_reference} />
                      </div>
                      <div class="uk-width-1-1">
                        <FormWidget id={`form-${unit.id}-type-ref-link`} label="Ref. link" type="input-text" bind:value={unit.type_reference_link} />
                      </div>
                      <div class="uk-width-1-1">
                        <FormWidget id={`form-${unit.id}-type-note`} label="Type Note" type="input-text" bind:value={unit.type_note} />
                      </div>
                      <div class="uk-width-1-1 uk-grid-small">
                        <h4 class="uk-heading-bullet">多媒體檔案</h4>
                      </div>
                      <div class="uk-width-1-1 uk-grid-small">
                        <h4 class="uk-heading-bullet">種子</h4>
                      </div>
                      <div class="uk-width-1-1 uk-grid-small">
                        <h4 class="uk-heading-bullet">屬性</h4>
                      </div>
                      <div class="uk-width-1-1">
                        <AttributeBox
                          attrTypes={$allOptions.assertion_type_unit_list}
                          bind:values={unit.assertions}
                          optionKey={{value: 'display_name', text:'display_name'}}
                          />
                      </div>
                      <div class="uk-width-1-1 uk-grid-small">
                        <h4 class="uk-heading-bullet">標註</h4>
                      </div>
                      <div class="uk-width-1-1">
                        <AttributeBox
                          attrTypes={$allOptions.annotation_type_unit_list}
                          bind:values={unit.annotations}
                          />
                      </div>
                      <div class="uk-width-1-1 uk-grid-small">
                        <h4 class="uk-heading-bullet">交換記錄</h4>
                      </div>
                      <table class="uk-table uk-table-small">
                        <thead>
                          <tr>
                            <th>標題</th>
                            <th>類別</th>
                            <th>日期</th>
                          </tr>
                        </thead>
                        <tbody>
                          {#each unit.transactions as trans}
                            <tr>
                              <td>{trans.title}</td>
                              <td>{trans.display_transaction_type}</td>
                              <td>{trans.date}</td>
                            </tr>
                          {/each}
                        </tbody>
                      </table>
                      <div class="uk-width-1-1">
                        <button type="button" on:click|preventDefault={() => removeUnit(idx)} class="uk-button uk-button-secondary uk-form-small">刪除</button>
                      </div>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
            </table>
          </div>
        </fieldset>
      </div>
    </div>
  </form>
</main>

<style>
  .mg-form-part {
    padding: 2px 10px;
  }
  .mg-input-xsmall {
    width: 60px;
  }
  .mg-iden-box {
    margin: 2px 0px;
    border: 3px dotted #eee;
    background: #f7f7f7;
  }
  .mg-background-label {
    background: #c9e5f2;
    padding: 4px;
    border: 2px solid #acacac;
  }
</style>
