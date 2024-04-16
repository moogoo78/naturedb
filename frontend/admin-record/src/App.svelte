<script>
  import { onMount } from 'svelte';
  import { HOST, RECORD_ID, allOptions, values } from './stores.js';
  import Select2a from './lib/Select2a.svelte'
  import FormWidget from './lib/FormWidget.svelte';
  import { fetchData, filterItems, convertDDToDMS, convertDMSToDD } from './utils.js';

  let formValues = {};
  let fetchOptions = {
    identificationTaxon: [],
    namedAreaAdmin: [],
  };
  let fetchLoading = {
    identificationTaxon: [],
    namedAreaAdmin: false,
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
  let tmpNamedAreasAdmin = '';

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
      let m = tmpCoordinates.lonMin.value;

      if (d >= 0 && d <= 180) {
        tmpCoordinates.lonDeg.classList.remove('uk-form-danger');
        if (m >= 0 && m <= 60) {
          const DMSList = [
            tmpCoordinates.lonDir.value,
            d,
            m,
            tmpCoordinates.lonSec.value,
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
      let m2 = tmpCoordinates.latMin.value;

      if (d2 >= 0 && d2 <= 90) {
        tmpCoordinates.latDeg.classList.remove('uk-form-danger');
        if (m2 >= 0 && m2 <= 60) {
          const DMSList = [
            tmpCoordinates.latDir.value,
            d2,
            m2,
            tmpCoordinates.latSec.value,
          ];
          console.log(DMSList, convertDMSToDD(DMSList));
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
    console.log($allOptions, $values);

    // apply data
    formValues.field_number = $values.field_number;
    formValues.collect_date = $values.collect_date;
    formValues.collect_date_text = $values.collect_date_text;
    formValues.companion_text = $values.companion_text;
    formValues.companion_en_text = $values.companion_en_text;
    formValues.longitude_decimal = $values.longitude_decimal;
    formValues.latitude_decimal = $values.latitude_decimal;
    formValues.verbatim_latitude = $values.verbatim_latitude;
    formValues.verbatim_longitude = $values.verbatim_longitude;
    formValues.altitude = $values.altitude;
    formValues.altitude2 = $values.altitude2;
    formValues.collector = {
      text: $values.collector.display_name,
      value: $values.collector.id
    };
    formValues.assertions = {};
    for (const [name, data] of Object.entries($values.assertions)) {
      formValues.assertions[name] = {text: data, value: data};
    }
    formValues.identifications = $values.identifications.map( (x) => {
      fetchOptions.identificationTaxon.push([]);
      fetchLoading.identificationTaxon.push(false);
      if (x.identifier) {
        x.identifier = {
          text: x.identifier.display_name,
          value: x.identifier.id,
        }
      }
      return x;
    });

    formValues.units = $values.units.map( (item) => {
      let tmp = {...item.assertions};
      for (const [name, data] of Object.entries(tmp)) {
        tmp[name] = {text: data.value, value: data.value};
      }
      return {
        ...item,
        assertions: tmp,
      }
    })

    formValues.named_areas = {};
    for(const [name, data] of Object.entries($values.named_areas)) {
      formValues.named_areas[name] = {
        text: data.display_name,
        value: data.id,
      };
    }
  }; // end of init
  init();

  const onNamedAreaAdminInput = async (input) => {
    if (input) {
      if (input.slice(0, 1) === '台') {
        input = input.replace('台', '臺');
      }
      fetchLoading.namedAreaAdmin = true;
      let url = `${$HOST}/api/v1/named-areas?filter={"q": "${input}","area_class_id":[7,8,9]}`;
      let results = await fetchData(url);
      let options = results.data;
      fetchOptions = {
        ...fetchOptions,
        namedArea: options.map( (x) => ({text: x.display_name, value: x.id}))
      };
      fetchLoading.namedAreaAdmin = false;
    }
  }

  const onNamedAreaAdminClear = () => {
    tmpNamedAreasAdmin = '';
  }

  const onNamedAreaAdminSelect = async (selected) => {
    formValues.named_areas__admin = selected;
    let url = `${$HOST}/api/v1/named-areas/${selected.value}?parents=1`;
    let result = await fetchData(url);
    let displayList = result.higher_area_classes.map( x => {
      return x.display_text;
    });
    displayList.push(selected.text);
    tmpNamedAreasAdmin = displayList.join(' ,');
  }

  const onNamedAreaAdminLonLat = async () => {
    const lon = tmpCoordinates.lonDD;
    const lat = tmpCoordinates.latDD;

    if (lon && lon.value && lat && lat.value) {
      const ft = JSON.stringify({
        within: {
          srid: 4326,
          point: [lon.value, lat.value],
        }
      });
      let result = await fetchData(`${$HOST}/api/v1/named-areas?filter=${ft}`);
      let x = result.data[result.data.length-1];
      formValues.named_areas__admin = {text: x.display_name, value: x.id};
      let displayList = result.data.map( x => {
        return x.display_name;
      });
      tmpNamedAreasAdmin = displayList.join(' ,');
    }
  }

  const onIdentificationTaxonInput = async (input, index) => {
    if (input) {
      fetchLoading.identificationTaxon[index] = true;
      let url = `${$HOST}/api/v1/taxa?filter={"q": "${input}"}`;
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

  const onSubmit = (e) => {
    console.log(formValues);

    //async function postData(url = "", data = {}) {
    // Default options are marked with *
    fetch(`${$HOST}/api/v1/admin/records/${$RECORD_ID}`, {
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
      });
  }


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
</script>

<main>
  <form id="record-form" class="uk-form-stacked" method="POST" action="/admin/records/136396">
  <!-- <input id="record-id" type="hidden" name="record_id" value="136396"> -->
  <!-- <input type="hidden" name="collection_id" value="1"> -->
  <p>Collection: <span class="uk-label uk-label-warning">HAST</span></p>
  </form>

  <form class="uk-grid-collapse uk-child-width-1-2" uk-grid>
    <div>
    </div>
    <div>
      <button class="uk-button uk-button-primary" type="submit" on:click|preventDefault={onSubmit}>送出</button>
    </div>
    <div><!-- left side -->
      <div class="uk-child-width-expand uk-grid-collapse" uk-grid>
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
          <div class="uk-child-width-1-2 uk-grid-collapse" uk-grid>
            <div>
              <FormWidget id="form-date" label="採集日期" type="input-date" bind:value={formValues.collect_date} />
            </div>
            <div>
              <FormWidget id="form-date-text" label="採集日期(verbatim)" type="input-text" placeholder="1990 or 1992-03" bind:value={formValues.collect_date_text}/>
            </div>
            <div>
              <FormWidget id="form-collector-text" label="隨同人員" type="textarea-read" bind:value={formValues.companion_text} />
            </div>
            <div>
              <FormWidget id="form-collector-text" label="隨同人員(英文)" type="textarea-read" bind:value={formValues.companion_en_text} />
            </div>
          </div>
          <div class="uk-width-1-1 uk-grid-small" uk-grid>
            <h4 class="uk-heading-bullet">地理坐標系統</h4>
          </div>
          <div class="uk-child-width-1-1 uk-grid-small" uk-grid>
            <div>
              <div uk-grid>
                <div class="uk-width-auto">
                  <ul class="uk-tab-left" uk-tab="connect: #component-tab-left;">
                    <li><a href="#">十進位</a></li>
                    <li><a href="#">度分秒(60進位)</a></li>
                    <li><a href="#">Verbatim經緯度</a></li>
                  </ul>
                </div>
                <div class="uk-width-expand">
                  <ul id="component-tab-left" class="uk-switcher">
                    <li>
                      <div uk-grid>
                        <div class="uk-width-1-2">
                            <FormWidget>
                              <svelte:fragment slot="label">
                                <label class="uk-width-auto" for="form-lon-decimal">經度(十進位)</label>
                              </svelte:fragment>
                              <svelte:fragment slot="control">
                                <input type="text" id="form-lon-decimal" class="uk-input uk-form-small" on:input={(e) => syncCoordinates(e.target.value, 'longitudeDecimal')} bind:this={tmpCoordinates.lonDD} value={formValues.longitude_decimal} />
                              </svelte:fragment>
                            </FormWidget>
                        </div>
                        <div class="uk-width-1-2">
                            <FormWidget>
                              <svelte:fragment slot="label">
                                <label class="uk-width-auto" for="form-lon-decimal">緯度(十進位)</label>
                              </svelte:fragment>
                              <svelte:fragment slot="control">
                                <input type="text" id="form-lat-decimal" class="uk-input uk-form-small" on:input={(e) => syncCoordinates(e.target.value, 'latitudeDecimal')} bind:this={tmpCoordinates.latDD} value={formValues.latitude_decimal} />
                              </svelte:fragment>
                            </FormWidget>
                        </div>
                      </div>
                    </li>
                    <li>
                      <div class="uk-flex">
                        <div>
                          <FormWidget>
                            <svelte:fragment slot="label">
                              <label class="uk-width-auto" for="converter-longitude-direction">東西經</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <select class="uk-select uk-form-small uk-width-small" id="converter-longitude-direction" on:input={(e) => syncCoordinates(e.target.value, 'longitudeDMS')} bind:this={tmpCoordinates.lonDir}>
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
                              <label class="uk-width-auto" for="converter-longitude-degree">° (度)</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <input class="uk-input uk-form-small uk-width-small" type="text" id="converter-longitude-degree" on:input={(e) => syncCoordinates(e.target.value, 'longitudeDMS')} bind:this={tmpCoordinates.lonDeg}/>
                            </svelte:fragment>
                          </FormWidget>
                        </div>
                        <div>
                          <FormWidget>
                            <svelte:fragment slot="label2">
                              <label class="uk-width-auto" for="converter-longitude-minute">' (分)</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <input class="uk-input uk-form-small uk-width-small" type="text" id="converter-longitude-minute" on:input={(e) => syncCoordinates(e.target.value, 'longitudeDMS')} bind:this={tmpCoordinates.lonMin}/>
                            </svelte:fragment>
                          </FormWidget>
                        </div>
                        <div>
                          <FormWidget>
                            <svelte:fragment slot="label2">
                              <label class="uk-width-auto" for="converter-longitude-second">" (秒)</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <input class="uk-input uk-form-small uk-width-small" type="text" id="converter-longitude-second" on:input={(e) => syncCoordinates(e.target.value, 'longitudeDMS')}  bind:this={tmpCoordinates.lonSec} />
                            </svelte:fragment>
                          </FormWidget>
                        </div>
                      </div>
                      <div class="uk-flex">
                        <div>
                          <FormWidget>
                            <svelte:fragment slot="label">
                              <label class="uk-width-auto" for="converter-latitude-degree">南北緯</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <select class="uk-select uk-form-small uk-width-small" id="converter-latitude-direction" on:change={(e) => syncCoordinates(e.target.value, 'latitudeDMS')} bind:this={tmpCoordinates.latDir}>
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
                              <label class="uk-width-auto" for="converter-altitude-degree"> ° (度)</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <input class="uk-input uk-form-small uk-width-small" type="text" id="converter-altitude-degree" on:input={(e) => syncCoordinates(e.target.value, 'latitudeDMS')} bind:this={tmpCoordinates.latDeg} />
                            </svelte:fragment>
                          </FormWidget>
                        </div>
                        <div>
                          <FormWidget>
                            <svelte:fragment slot="label2">
                              <label class="uk-width-auto" for="converter-altitude-minute">' (分)</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <input class="uk-input uk-form-small uk-width-small" type="text" id="converter-altitude-minute" on:input={(e) => syncCoordinates(e.target.value, 'latitudeDMS')} bind:this={tmpCoordinates.latMin} />
                            </svelte:fragment>
                          </FormWidget>
                        </div>
                        <div>
                          <FormWidget>
                            <svelte:fragment slot="label2">
                              <label class="uk-width-auto" for="converter-altitude-second">" (秒)</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <input class="uk-input uk-form-small uk-width-small" type="text" id="converter-altitude-second" on:input={(e) => syncCoordinates(e.target.value, 'latitudeDMS')} bind:this={tmpCoordinates.latSec} />
                            </svelte:fragment>
                          </FormWidget>
                        </div>
                      </div>
                    </li>
                    <li>
                      <div class="uk-width-1-1 uk-grid-collapse" uk-grid>
                        <div class="uk-width-1-2">
                          <FormWidget id="form-lon-decimal" label="Verbatim 經度" type="input-text" bind:value={formValues.verbatim_longitude} />
                        </div>
                        <div class="uk-width-1-2">
                          <FormWidget id="form-lat-decimal" label="Verbatim 緯度" type="input-text" bind:value={formValues.verbatim_latitude}/>
                        </div>
                      </div>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
          <div class="uk-width-1-1 uk-grid-small" uk-grid>
            <h4 class="uk-heading-bullet">地點資訊</h4>
          </div>
          <div class="uk-width-1-1 uk-grid-collapse" uk-grid>
            <div class="uk-width-1-2">
              <FormWidget id="form-altitude" label="海拔" type="input-text" bind:value={formValues.altitude} />
            </div>
            <div class="uk-width-1-2">
              <FormWidget id="form-altitude2" label="海拔2" type="input-text" bind:value={formValues.altitude2}/>
            </div>
          </div>
          <div class="uk-width-1-1 uk-grid-collapse" uk-grid>
            <div class="uk-width-expand">
              <FormWidget>
                <svelte:fragment slot="label">
                  <label class="uk-width-auto" for="form-named-area">選擇行政區名稱</label>
                </svelte:fragment>
                <svelte:fragment slot="control">
                  {#if fetchLoading.namedAreaAdmin === true}
                    <div uk-spinner></div>
                  {/if}
                  <Select2a
                    options={fetchOptions.namedArea}
                    onSelect={onNamedAreaAdminSelect}
                    value={formValues.named_areas__admin}
                    onInput={onNamedAreaAdminInput}
                    onClear={onNamedAreaAdminClear}
                  />
                </svelte:fragment>
              </FormWidget>
            </div>
            <div class="uk-width-auto">
              <button class="uk-button uk-button-primary" on:click|preventDefault={onNamedAreaAdminLonLat}>從經緯度取得</button>
            </div>
          </div>
          <div class="uk-width-1-1">
            <span>完整行政區名稱</span>: <span class="uk-text-primary">{tmpNamedAreasAdmin}</span>
          </div>
          {#each Object.entries($allOptions.named_area) as [name, data]}
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
        </fieldset>
      </div>
      <div class="uk-child-width-1-1- uk-grid-small" uk-grid>
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
                    options={data.options.map( x => ({text: x.display_name, value: x.id}))}
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
      <div class="uk-child-width-expand uk-grid-collapse" uk-grid>
        <fieldset>
          <legend>鑑定</legend>
          <button class="uk-button uk-button-small uk-button" on:click|preventDefault={() => {
            let len = formValues.identifications.length;
            formValues.identifications = [...formValues.identifications, {sequence: len}];
            }}>新增</button>
          <div class="uk-child-width-1-1 uk-grid-collapse" uk-grid>
            <table class="uk-table uk-table-small uk-table-divider">
              <thead>
                <tr>
                  <th>#</th>
                  <th>taxon</th>
                  <th>鑒定者</th>
                  <th>鑒定日期</th>
                  <th>Verbatim鑒定日期</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {#each formValues.identifications as idObj, idx}
                  <tr>
                    <td>{idx+1}</td>
                    <td>
                      {#if fetchLoading.identificationTaxon[idx] === true}
                        <div uk-spinner></div>
                      {/if}
                      <Select2a
                        options={fetchOptions.identificationTaxon[idx]}
                        onSelect={(selected) => {
                          idObj.taxon = selected;
                        }}
                        value={idObj.taxon}
                        onInput={(input) => onIdentificationTaxonInput(input, idx)}
                        />

                    <td>
                      <Select2a
                        options={$allOptions.identifier_list.map( x => ({text: x.display_name, value: x.id}))}
                        onSelect={(selected) => {
                          idObj.identifier = selected;
                        }}
                        value={idObj.identifier}
                        onClear={()=>{idObj.identifier=null;}}
                      />
                    </td>
                    <td>
                      <input class="uk-input uk-form-small" type="date" bind:value={idObj.date}/>
                    </td>
                    <td>
                      <input class="uk-input uk-form-small" type="text" bind:value={idObj.verbatim_date}/>
                    </td>
                    <td>
                      <button type="button" on:click|preventDefault={() => removeIdentification(idx)}>刪除</button>
                    </td>
                </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </fieldset>
      </div>
      <div class="uk-child-width-expand uk-grid-collapse" uk-grid>
        <fieldset>
          <legend>標本</legend>
          <button class="uk-button uk-button-small uk-button" on:click|preventDefault={() => {
            formValues.units = [...formValues.units, {assertions:{}}];
            }}>新增</button>
          <div class="uk-child-width-1-1 uk-grid-collapse" uk-grid>
            <table class="uk-table uk-table-small uk-table-divider uk-table-striped">
              <thead>
                <tr>
                  <th>館號</th>
                  <th>壓製日期</th>
                  <th>取得方式</th>
                  <th>取得日期</th>
                  <th>標本來源</th>
                  <th>發佈狀態</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {#each formValues.units as unit, idx}
                <tr>
                  <td>
                    <input type="text" class="uk-input uk-form-small" bind:value={unit.accession_number} />
                  </td>
                  <td>
                    <input type="date" class="uk-input uk-form-small" bind:value={unit.preparation_date} />
                  </td>
                  <td>
                    <select class="uk-select uk-form-small">
                      <option value="">-- 選擇 --</option>
                      {#each $allOptions.transaction_type as data}
                        <option value={data[0]}>{data[1]}</option>
                      {/each}
                    </select>
                  </td>
                  <td>
                    <input type="date" class="uk-input uk-form-small" bind:value={unit.acquiration_date} />
                  </td>
                  <td>
                    <select class="uk-select uk-form-small">
                      <option value="">-- 選擇 --</option>
                      {#each $allOptions.type_status as item}
                        <option value={item[0]}>{item[1].toUpperCase()}</option>
                      {/each}
                    </select>
                  </td>
                  <td>
                    <select class="uk-select uk-form-small">
                      <option value="">-- 選擇 --</option>
                      {#each $allOptions.pub_status as item}
                        <option value={item[0]}>{item[1]}</option>
                      {/each}
                    </select>
                  </td>
                  <td>
                    <button uk-toggle="target: #{`unit-${unit.id}-extend`}" type="button">展開</button>
                    <button type="button" on:click|preventDefault={() => removeUnit(idx)}>刪除</button>
                  </td>
                </tr>
                <tr id={`unit-${unit.id}-extend`} hidden>
                  <td colspan="7">
                    <div class="uk-child-width-1-1 uk-grid-small" uk-grid>
                      {#each $allOptions.assertion_type_unit_list as atype}
                        {#if atype.input_type === "select"}
                          <FormWidget>
                            <svelte:fragment slot="label">
                              <label class="uk-width-auto" for="form">{atype.label}</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <Select2a
                                options={atype.options.map( x => ({text: x.display_name, value: x.id}))}
                                value={unit.assertions[atype.name]}
                                onSelect={(selected)=>{
                                  unit.assertions[atype.name] = selected;
                                }}
                                onClear={()=>{unit.assertions[atype.name]=null;}}
                                />
                            </svelte:fragment>
                          </FormWidget>
                        {:else if atype.input_type === "input"}
                          <FormWidget id="" value={atype.value} label={atype.label} type="input-text"></FormWidget>
                        {/if}
                      {/each}
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
</style>
