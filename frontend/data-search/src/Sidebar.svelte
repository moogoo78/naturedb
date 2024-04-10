<script>
  import FormWidget from './FormWidget.svelte';
  import Select2 from './Select2.svelte';
  import { HOST, register, unitResults, searching, filterTags, pagination, formValues, isLanding } from './stores.js';
  import { fetchData, appendQuery } from './utils.js';

  export let goSearch;
  export let toggleOpen;

  //export let values = {};
  let select2State = {
    option: {},
    loading: {},
    group: {},
    display: {},
  };
  let searchbarQuery; // for searchbar value

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
      fetchData(url, (results)=> {
        select2State.option[key] = results.data;
        select2State.loading[key] = false;
      });
    }));
    //console.log('allOptions:', results);
  }; // end of init

  const onSelect2 = (key, value, label, data) => {
    formValues.set({
      ...$formValues,
      [key]: {
        value: value,
        display: label,
        name: key,
      }
    });
    if (data) {
      let target = data.target;
      let arr = $register[target].fetch.split('?');
      let url = arr[0];
      let searchParams = appendQuery(arr[1], 'filter', data.query)
      url = `${$HOST}/${url}?${searchParams.toString()}`;
      select2State.loading[target] = true;
      fetchData(url, (results)=> {
        select2State.option[target] = results.data;
        select2State.loading[target] = false;
      });
      // reset group decent select options
      if (data.hasOwnProperty('resets')) {
        for (let i of data['resets']) {
          select2State.option[i] = [];
          formValues[i] = null;
        }
      }
    }
  }

  const onSelect2
    formValues[key] = null;
    if (data && data.hasOwnProperty('resets')) {
      for (let i of data['resets']) {
        select2State.option[i] = [];
        formValues[i] = null;
      }
    }
  }

  const handleSelectContinent = (e) => {
    console.log(e.target.value);
    let arr = $register.continent.fetch.split('?');
    let url = arr[0];
    let searchParams = appendQuery(arr[1], 'filter', {'continent': e.target.value})
    url = `${$HOST}/${url}?${searchParams.toString()}`;
    fetchData(url, (results) => {
      select2State.option.country = results.data;
      console.log(results.data)
      
      })
  }

  const onSubmit = (e) => {
    e.preventDefault();
    if ($isLanding) {
      isLanding.set(false);
    }
    //touchedFields = { name: true, length: true, type: true };
    //if (!Object.keys(errors).length) {
    //onSubmit(result);
    //}
    goSearch();
  }

  init();
  $:{
    console.log('$', select2State, $formValues);
  }
</script>

<div class="uk-card uk-card-default uk-card-small uk-card-body">
  <div class="uk-flex uk-flex-between uk-flex-top">
    <h4 class="uk-text-primary">篩選</h4>
    <button type="button" aria-label="Close" uk-close on:click|preventDefault={toggleOpen}></button>
  </div>
  <form class="uk-form-stacked">
    <div class="uk-flex uk-flex-right">
      <button class="uk-button uk-button-primary uk-button-small" type="button" on:click={onSubmit}>送出</button>
    </div>
    <fieldset class="uk-fieldset">
      <h5 class="uk-heading-line uk-text-center uk-text-muted filter-title"><span>物種</span></h5>
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
            <Select2 options={select2State.option.genus} optionText="display_name" optionValue="id" disabled={(select2State.option.genus && select2State.option.genus.length > 0) ? false : true} onCallback={(x, y) => onSelect2('genus', x , y, {target: 'species', query: {parent_id: x}})} value={$formValues.genus} />
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">種名 (Species)</svelte:fragment>
        <svelte:fragment slot="control">
          {#if select2State.loading.species === false}
            <Select2 options={select2State.option.species} optionText="display_name" optionValue="id" disabled={(select2State.option.species && select2State.option.species.length > 0) ? false : true} onCallback={(x, y) => onSelect2('species', x, y)} value={formValues.species} data/>
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
          <select class="uk-select" on:change={handleSelectContinent}>
            <option>-- 選擇 --</option>
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
        <svelte:fragment slot="label">國家/地區(修改中)</svelte:fragment>
        <svelte:fragment slot="control">
          {#if select2State.loading.country === false}
            <Select2 options={select2State.option.country} optionText="display_name" optionValue="id" onCallback={(x) => onSelect2('country', x, {target: 'adm1', query: {parent_id: x}, resets: ['adm2']})} onCallbackClear={ () => onSelect2Clear('country', {resets: ['adm2', 'adm3']})}  value={$formValues.country} />
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">海拔</svelte:fragment>
        <svelte:fragment slot="control">
          <div class="uk-flex uk-flex-row uk-width-1-1">
            <select class="uk-select uk-margin-small-right" bind:value={$formValues.altitude_contidion}>
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
      <button class="uk-button uk-button-primary uk-button-large uk-width-1-1" type="button" on:click={onSubmit}>送出</button>
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
  .fieldset {
    border: 2px dashed #eee;
    border-radius: 4px;
    padding: 20px;
  }

  .en-dash {
    float: left;
    margin-left: 0px;
    line-height: 1.5;
    content: "\2013";
    font-size: 24px;
  }
</style>
