<script>
  import { HOST, allOptions, values } from './stores.js';
  import Select2a from './lib/Select2a.svelte'
  import FormWidget from './lib/FormWidget.svelte';
  import { fetchData } from './utils.js';

  const formValues = {};
  const init = async () => {
    console.log($allOptions);
    console.log($values);
    // apply data
    formValues.field_number = $values.field_number;
    formValues.collect_date = $values.collect_date;
    formValues.collect_date_text = $values.collect_date_text;
    formValues.companion_text = $values.companion_text;
    formValues.companion_en_text = $values.companion_en_text;
    formValues.latitude_decimal = $values.latitude_decimal;
    formValues.longitude_decimal = $values.longitude_decimal;
    formValues.verbatim_latitude = $values.verbatim_latitude;
    formValues.verbatim_longitude = $values.verbatim_longitude;
    formValues.altitude = $values.altitude;
    formValues.altitude2 = $values.altitude2;
    formValues.collector = $values.collector;
    formValues.units = $values.units;
    formValues.identifications = $values.identifications;
  }; // end of init
  init();

  const onSelect2 = (key, value, label, data) => {
    formValues[key] = {
      value: value,
      display: label,
      name: key,
    };
  }

  const onSubmit = (e) => {
    console.log(formValues);
  }

  //$: {console.log(select2State);}
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
                    options={$allOptions.collector_list}
                    onCallback={(x, y) => onSelect2('collector', x, y)}
                    value={formValues.collector}
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
                          <FormWidget id="form-lon-decimal" label="經度(十進位)" type="input-text" bind:value={formValues.longitude_decimal} />
                        </div>
                        <div class="uk-width-1-2">
                          <FormWidget id="form-lat-decimal" label="緯度(十進位)" type="input-text" bind:value={formValues.latitude_decimal}/>
                        </div>
                      </div>
                    </li>
                    <li>
                      <div class="uk-flex">
                        <div>
                          <FormWidget>
                            <svelte:fragment slot="label">
                              <label class="uk-width-auto" for="converter-longitude-degree">東西經</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <select class="uk-select uk-form-small uk-width-small" id="converter-longitude-direction">
                                <option value="">-- 選擇--</option>
                                <option value="1">東經</option>
                                <option value="-1">西經</option>
                              </select>
                            </svelte:fragment>
                          </FormWidget>
                        </div>
                        <div>
                          <FormWidget>
                            <svelte:fragment slot="label">
                              <label class="uk-width-auto" for="converter-longitude-degree">經度: ° (度)</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <input class="uk-input uk-form-small uk-width-small" type="text" id="converter-longitude-degree" value=""/>
                            </svelte:fragment>
                          </FormWidget>
                        </div>
                        <div>
                          <FormWidget>
                            <svelte:fragment slot="label">
                              <label class="uk-width-auto" for="converter-longitude-minute">經度: ' (分)</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <input class="uk-input uk-form-small uk-width-small" type="text" id="converter-longitude-minute" value=""/>
                            </svelte:fragment>
                          </FormWidget>
                        </div>
                        <div>
                          <FormWidget>
                            <svelte:fragment slot="label">
                              <label class="uk-width-auto" for="converter-longitude-second">經度: " (秒)</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <input class="uk-input uk-form-small uk-width-small" type="text" id="converter-longitude-second" value=""/>
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
                              <select class="uk-select uk-form-small uk-width-small" id="converter-latitude-direction">
                                <option value="">-- 選擇--</option>
                                <option value="1">北緯</option>
                                <option value="-1">南緯</option>
                              </select>
                            </svelte:fragment>
                          </FormWidget>
                        </div>
                        <div>
                          <FormWidget>
                            <svelte:fragment slot="label">
                              <label class="uk-width-auto" for="converter-altitude-degree">緯度: ° (度)</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <input class="uk-input uk-form-small uk-width-small" type="text" id="converter-altitude-degree" value=""/>
                            </svelte:fragment>
                          </FormWidget>
                        </div>
                        <div>
                          <FormWidget>
                            <svelte:fragment slot="label">
                              <label class="uk-width-auto" for="converter-altitude-minute">緯度: ' (分)</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <input class="uk-input uk-form-small uk-width-small" type="text" id="converter-altitude-minute" value=""/>
                            </svelte:fragment>
                          </FormWidget>
                        </div>
                        <div>
                          <FormWidget>
                            <svelte:fragment slot="label">
                              <label class="uk-width-auto" for="converter-altitude-second">緯度: " (秒)</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <input class="uk-input uk-form-small uk-width-small" type="text" id="converter-altitude-second" value=""/>
                            </svelte:fragment>
                          </FormWidget>
                        </div>
                      </div>
                    </li>
                    <li>
                      <div class="uk-width-1-1 uk-grid-collapse" uk-grid>
                        <div class="uk-width-1-2">
                          <FormWidget id="form-lon-decimal" label="Verbatim 經度" type="input-text" bind:value={formValues.verbatim_decimal} />
                        </div>
                        <div class="uk-width-1-2">
                          <FormWidget id="form-lat-decimal" label="Verbatim 緯度" type="input-text" bind:value={formValues.verbatim_decimal}/>
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
                  <label class="uk-width-auto" for="form-named-area">選擇地點名稱</label>
                </svelte:fragment>
                <svelte:fragment slot="control">
                  <Select2a
                    fetch={`${$HOST}/api/v1/named-areas?filter={"q":"__q__","area_class_id":[7,8,9]}`}
                    onCallback={(x, y) => onSelect2('collector', x, y)}
                    value={formValues.collector}
                    loading={false}
                    />
                </svelte:fragment>
              </FormWidget>
            </div>
            <div class="uk-width-auto">
              <button class="uk-button uk-button-primary" on:click|preventDefault={(e) => {}}>從經緯度取得</button>
            </div>
          </div>
        </fieldset>
      </div>
      <div class="uk-child-width-1-1- uk-grid-small" uk-grid>
        <button class="uk-button uk-button-default" type="button" uk-toggle="target: .toggle">Toggle</button>
        <div class="toggle" hidden>
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
                      options={data.options}
                      onCallback={(x, y) => onSelect2('collector', x, y)}
                      value={formValues.collector}
                      loading={false}
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
          <div class="uk-child-width-1-1 uk-grid-collapse" uk-grid>
            <table class="uk-table uk-table-small uk-table-divider">
              <thead>
                <tr>
                  <th>#</th>
                  <th>鑒定者</th>
                  <th>taxon</th>
                  <th>鑒定日期</th>
                  <th>Verbatim鑒定日期</th>
                </tr>
              </thead>
              <tbody>
                {#each formValues.identifications as idObj, idx}
                <tr>
                  <td>{idx+1}</td>
                  <td>
                    <Select2a
                      options={$allOptions.identifier_list}
                      onCallback={(x, y) => onSelect2('identifier', x, y)}
                      value={formValues.idObj}
                      />
                  <td>
                    <Select2a
                      options={$allOptions.identifier_list}
                      onCallback={(x, y) => onSelect2('identifier', x, y)}
                      value={formValues.idObj}
                      />
                  </td>
                  <td>
                    <input class="uk-input uk-form-small" type="date" bind:value={idObj.date}/>
                  </td>
                      <td>
                        <input class="uk-input uk-form-small" type="text" bind:value={idObj.verbatim_date}/>
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
                  <th>toggle</th>
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
                  </td>
                </tr>
                <tr id={`unit-${unit.id}-extend`} hidden>
                  <td colspan="7">
                    <div class="uk-child-width-1-1 uk-grid-small" uk-grid>
                      {#each $allOptions.assertion_type_unit_list as data}
                        {#if data.input_type === "select"}
                          <FormWidget>
                            <svelte:fragment slot="label">
                              <label class="uk-width-auto" for="form">{data.label}</label>
                            </svelte:fragment>
                            <svelte:fragment slot="control">
                              <Select2a
                                options={data.options}
                                onCallback={(x, y) => onSelect2('collector', x, y)}
                                value={formValues.collector}
                                loading={false}
                                />
                            </svelte:fragment>
                          </FormWidget>
                        {:else if data.input_type === "input"}
                          <FormWidget id="" value={data.value} label={data.label} type="input-text"></FormWidget>
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
