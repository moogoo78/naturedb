<script>
  import FormWidget from './FormWidget.svelte';
  import Select2 from './Select2.svelte';
  import { HOST, register, formant, formValues } from '../stores.js';
  import { fetchData, appendQuery } from './utils.js';

  export let isSidebarOpen;
  export let isLanding;

  //$: formValues = $formant.formValues;

  let select2State = {
    option: {},
    loading: {},
    group: {},
    display: {},
  };

  const init = async () => {
    const urls = [];
    //let tmpGroup = [];
    for (const [key, data] of Object.entries($register)) {
      if (['combobox', 'select'].indexOf(data.type) > -1) {
        if ('isFetchInit' in data && data.isFetchInit) {
          const url = `${$HOST}/${data.fetch}`;
          urls.push([key, url]);
        }
        select2State.option[key] = [];
        select2State.loading[key] = false;
      }
      // if ('group' in data) {
      //   if (!tmpGroup.hasOwnProperty(data.group.name)) {
      //     tmpGroup[data.group.name] = [];
      //   }
      //   tmpGroup[data.group.name].push([data.group.index, key]);
      // }
    }
    // for (const key in tmpGroup) {
    //   const sorted = tmpGroup[key].sort((a, b) => a[0] - b[0]);
    //   select2State.group[key] = sorted.map( x => x[1]); // remove sort index
    // }

    const results = await Promise.all(urls.map(async ([key, url]) => {
      select2State.loading[key] = true;
      let results = await fetchData(url);
      select2State.option[key] = results.data;
      select2State.loading[key] = false;
    }));
  }; // end of init

  const onSelect2 = async (key, value, label, data) => {
    formValues.set({
      ...$formValues,
      [key]: {
        value: value,
        display: label,
        name: key,
      }
    });

    if (data?.target) {
      let target = data.target;
      let arr = $register[target].fetch.split('?');
      let searchParams = appendQuery(arr[1], 'filter', data.query)
      let url = arr[0];
      url = `${$HOST}/${url}?${searchParams.toString()}`;
      select2State.loading[target] = true;
      let results = await fetchData(url);
      select2State.option[target] = results.data;
      select2State.loading[target] = false;

      // reset group decent select options
      if (data.hasOwnProperty('resets')) {
        for (let i of data['resets']) {
          select2State.option[i] = [];
          $formValues[i] = null;
        }
      }
    }
  }

  const onSelect2Clear = (key, data) => {
    let values = {...$formValues};
    delete values[key];
    if (data?.resets) {
      for(let x of data.resets) {
        delete values[x];
      }
    }
    formValues.set(values);
  };

  const handleSelectContinent = async (e) => {
    let arr = $register.continent.fetch.split('?');
    let url = arr[0];
    let searchParams = appendQuery(arr[1], 'filter', {'continent': e.target.value})
    url = `${$HOST}/${url}?${searchParams.toString()}`;
    let results = await fetchData(url);
    select2State.option.country = results.data;
  }


  const onSubmit = () => {
    //isSidebarOpen = !isSidebarOpen;
    if (isLanding === true) {
      isLanding = false;
    }

    //touchedFields = { name: true, length: true, type: true };
    //if (!Object.keys(errors).length) {
    //onSubmit(result);
    //}
    //console.log('--------', $formValues);
    formant.goSearch({formValues:$formValues});
  }

  const onScientificNameInput = async (input) => {
    if (input && input.length >= 2) {
      select2State.loading.scientific_name = true;
      let url = '';
      if (input.length >= 4) {
        url = `${$HOST}/api/v1/taxa?filter={"q":"${input}"}`;
      } else {
        url = `${$HOST}/api/v1/taxa?filter={"q":"${input}"}&range=[0, 100]`;
      }
      let results = await fetchData(url);
      if (results.data) {
        select2State.option.scientific_name = results.data.map( (x) => ({display_name: x.display_name, value: x.id}));
      }
    }
  }
  init();
  $:{ console.log('$', select2State, $formValues); }
</script>

<div class="uk-card uk-card-default uk-card-small uk-card-body">
  <div class="uk-flex uk-flex-between uk-flex-top">
    <h4 class="uk-text-primary">篩選</h4>
    {#if !isLanding}
      <button type="button" aria-label="Close" uk-close on:click|preventDefault={()=>{isSidebarOpen = !isSidebarOpen}}></button>
    {/if}
  </div>
  <form class="uk-form-stacked" on:submit|preventDefault={onSubmit}>
    <div class="uk-flex uk-flex-between">
      <button class="uk-button uk-button-secondary uk-button-small" type="button" on:click={() => { formValues.set({}); }}>清除</button>
      <button class="uk-button uk-button-primary uk-button-small" type="submit">送出</button>
    </div>
    <fieldset class="uk-fieldset">
      <h5 class="uk-heading-line uk-text-center uk-text-muted filter-title"><span>物種</span></h5>
      <FormWidget>
        <svelte:fragment slot="label">學名</svelte:fragment>
        <svelte:fragment slot="control">
          <Select2
            options={select2State.option.scientific_name}
            optionText="display_name"
            optionValue="id"
            onCallback2={(x, y) => onSelect2('scientific_name', x, y)}
            onCallbackClear={ () => onSelect2Clear('scientific_name')}
            value={$formValues.scientific_name}
            onInput={onScientificNameInput}
            />
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">科名 (Family)</svelte:fragment>
        <svelte:fragment slot="control">
          {#if select2State.loading.family === false}
            <Select2 options={select2State.option.family} optionText="display_name" optionValue="id" onCallback={(x, y) => onSelect2('family', x, y, {target: 'genus', query: {parent_id: x}, resets: ['species']})} onCallbackClear={ () => onSelect2Clear('family', {resets: ['species', 'genus']})} value={$formValues.family} />
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">屬名 (Genus)</svelte:fragment>
        <svelte:fragment slot="control">
          {#if select2State.loading.genus === false}
            <Select2 options={select2State.option.genus} optionText="display_name" optionValue="id" disabled={(select2State.option.genus && select2State.option.genus.length > 0) ? false : true} onCallback={(x, y) => onSelect2('genus', x , y, {target: 'species', query: {parent_id: x}})} onCallbackClear={ () => onSelect2Clear('genus', {resets: ['species']})} value={$formValues.genus} />
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">種名 (Species)</svelte:fragment>
        <svelte:fragment slot="control">
          {#if select2State.loading.species === false}
            <Select2 options={select2State.option.species} optionText="display_name" optionValue="id" disabled={(select2State.option.species && select2State.option.species.length > 0) ? false : true} onCallback={(x, y) => onSelect2('species', x, y)} onCallbackClear={ () => onSelect2Clear('species')} value={$formValues.species} data/>
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
    </fieldset>
    <fieldset class="uk-fieldset">
      <h5 class="uk-heading-line uk-text-center uk-text-muted filter-title"><span>採集資訊</span></h5>
      <FormWidget>
        <svelte:fragment slot="label">採集者</svelte:fragment>
        <svelte:fragment slot="control">
          <Select2 options={select2State.option.collector} optionText="display_name" optionValue="id" onCallback={ (x, y) => onSelect2('collector', x, y)} onCallbackClear={ x => onSelect2Clear('collector')} value={$formValues.collector}/>
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">採集號</svelte:fragment>
        <svelte:fragment slot="control">
          <div class="uk-flex uk-flex-row uk-width-1-1">
            <input class="uk-input uk-margin-small-right" bind:value={$formValues.field_number} />
            <span class="en-dash">-</span>
            <input class="uk-input uk-margin-small-left" bind:value={$formValues.field_number2}/>
          </div>
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">採集日期</svelte:fragment>
        <svelte:fragment slot="control">
          <div uk-grid>
            <div class="uk-width-1-1">
              <input class="uk-input" type="date" bind:value={$formValues.collect_date} />
              <div class="uk-text-center">~</div>
              <input class="uk-input" type="date" bind:value={$formValues.collect_date2}/>
            </div>
          </div>
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">採集月份</svelte:fragment>
        <svelte:fragment slot="control">
              <select class="uk-select" bind:value={$formValues.collect_month}>
                <option value="">-- 選擇 --</option>
                <option value="1">1月</option>
                <option value="2">2月</option>
                <option value="3">3月</option>
                <option value="4">4月</option>
                <option value="5">5月</option>
                <option value="6">6月</option>
                <option value="7">7月</option>
                <option value="8">8月</option>
                <option value="9">9月</option>
                <option value="10">10月</option>
                <option value="11">11月</option>
                <option value="12">12月</option>
              </select>
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">洲/Continent</svelte:fragment>
        <svelte:fragment slot="control">
          <select class="uk-select" on:change={handleSelectContinent} bind:value={$formValues.continent}>
            <option value="">-- 選擇 --</option>
            <option value="asia">亞洲/Asia</option>
            <option value="europe">歐洲/Europe</option>
            <option value="americas">美洲/Americas</option>
            <option value="oceania">大洋洲/Oceania</option>
            <option value="africa">非洲/Africa</option>
            <option value="antarctica">南極洲/Antarctica</option>
          </select>
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">國家/地區</svelte:fragment>
        <svelte:fragment slot="control">
          {#if select2State.loading.country === false}
            <Select2 options={select2State.option.country} optionText="display_name" optionValue="id" onCallback={(x, y) => onSelect2('country', x, y, {target: 'adm1', query: {parent_id: x}, resets: ['adm2']})} onCallbackClear={ () => onSelect2Clear('country', {resets: ['adm1', 'adm2', 'adm3']})} value={$formValues.country} />
          {:else}
            <div uk-spinner></div>
              {/if}
            </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">行政區1</svelte:fragment>
        <svelte:fragment slot="control">
          {#if select2State.loading.adm1 === false}
            <Select2 options={select2State.option.adm1} optionText="display_name" optionValue="id" onCallback={(x, y) => onSelect2('adm1', x, y, {target: 'adm2', query: {parent_id: x}, resets: ['adm3']})} onCallbackClear={ () => onSelect2Clear('country', {resets: ['adm2', 'adm3']})} value={$formValues.adm1} />
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">行政區2</svelte:fragment>
        <svelte:fragment slot="control">
          {#if select2State.loading.adm2 === false}
            <Select2 options={select2State.option.adm2} optionText="display_name" optionValue="id" onCallback={(x, y) => onSelect2('adm2', x, y, {target: 'adm3', query: {parent_id: x}})} onCallbackClear={ () => onSelect2Clear('country', {resets: ['adm3']})} value={$formValues.adm2} />
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">行政區3</svelte:fragment>
        <svelte:fragment slot="control">
          {#if select2State.loading.adm3 === false}
            <Select2 options={select2State.option.adm3} optionText="display_name" optionValue="id" onCallback={(x, y) => onSelect2('adm3', x, y)} onCallbackClear={ () => onSelect2Clear('country')} value={$formValues.adm3} />
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">國家公園/保護留區</svelte:fragment>
        <svelte:fragment slot="control">
          {#if select2State.loading.named_area__park === false}
            <Select2 options={select2State.option.named_area__park} optionText="display_name" optionValue="id" onCallback={(x, y) => onSelect2('named_area__park', x, y)} onCallbackClear={ () => onSelect2Clear('named_area__park')} value={$formValues.named_area__park} />
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">地點名稱</svelte:fragment>
        <svelte:fragment slot="control">
          {#if select2State.loading.named_area__locality === false}
            <Select2 options={select2State.option.named_area__locality} optionText="display_name" optionValue="id" onCallback={(x, y) => onSelect2('named_area__locality', x, y)} onCallbackClear={ () => onSelect2Clear('named_area__locality')} value={$formValues.named_area__locality} />
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">海拔</svelte:fragment>
        <svelte:fragment slot="control">
          <div class="uk-flex uk-flex-row uk-width-1-1">
            <select class="uk-select uk-margin-small-right" bind:value={$formValues.altitude_condiction}>
              <option value="">-- 選擇 --</option>
              <option value="between">介於</option>
              <option value="gte">大於</option>
              <option value="lte">小於</option>
              <option value="eq">等於</option>
            </select>
            <input class="uk-input uk-margin-small-right" type="text" bind:value={$formValues.altitude}/>
            <span class="en-dash">-</span>
            <input class="uk-input uk-margin-small-left" type="text" bind:value={$formValues.altitude2}/>
          </div>
        </svelte:fragment>
      </FormWidget>
    </fieldset>
    <fieldset class="uk-fieldset">
      <h5 class="uk-heading-line uk-text-center uk-text-muted filter-title"><span>標本資訊</span></h5>
      <FormWidget>
        <svelte:fragment slot="label">館號</svelte:fragment>
        <svelte:fragment slot="control">
          <div class="uk-flex uk-flex-row uk-width-1-1">
            <input class="uk-input uk-margin-small-right" type="text" bind:value={$formValues.accession_number}/>
            <span class="en-dash">-</span>
            <input class="uk-input uk-margin-small-left" type="text" bind:value={$formValues.accession_number2}/>
          </div>
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">模式標本</svelte:fragment>
        <svelte:fragment slot="control">
          <select class="uk-select" bind:value={$formValues.type_status}>
            <option value="">-- 選擇 --</option>
            <option value="holotype">holotype</option>
            <option value="lectotype">lectotype</option>
            <option value="isotype">isotype</option>
            <option value="syntype">syntype</option>
            <option value="paratype">paratype</option>
            <option value="neotype">neotype</option>
            <option value="epitype">epitype</option>
          </select>
        </svelte:fragment>
      </FormWidget>
    </fieldset>
    <div class="uk-width-1-1@s">
      <hr class="uk-divider-icon">
      <button class="uk-button uk-button-primary uk-button-large uk-width-1-1" type="submit">送出</button>
    </div>
  </form>

  <!-- <div> -->
  <!--   <pre> -->
  <!--     {JSON.stringify($formValues, null, 2)} -->
  <!--     --- -->
  <!--     {JSON.stringify($filterTags, null, 2)} -->
  <!--   </pre> -->
  <!-- </div> -->

</div>

<style>
  .filter-title {
    font-size: 18px;
    font-weight: 500;
  }
  .search-filter {
    margin-top: 8px;
    border-radius: 4px;
  }
  .widget-container > div:not(:first-child) {
    margin-top: 16px;
  }
  /* .fieldset { */
  /*   border: 2px dashed #eee; */
  /*   border-radius: 4px; */
  /*   padding: 20px; */
  /* } */

  .en-dash {
    float: left;
    margin-left: 0px;
    line-height: 1.5;
    content: "\2013";
    font-size: 24px;
  }
</style>
