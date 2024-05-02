<script>
  import { onMount } from 'svelte';

  import FormWidget from './FormWidget.svelte';
  import Select2 from './Select2.svelte';
  import { HOST, register } from './stores.js';
  import { formant } from './formant.js';
  import { fetchData, appendQuery } from './utils.js';

  export let isSidebarOpen;
  export let isLanding;

  const init = async () => {
    let urls = [];
    let tmpGroup = [];
    for (const [key, data] of Object.entries($register)) {
      if (['combobox', 'select'].indexOf(data.type) >= 0) {
        $formant.selectState.option[key] = [];
        $formant.selectState.loading[key] = false;
        if ('isFetchInit' in data && data.isFetchInit) {
          const url = `${$HOST}/${data.fetch}`;
          urls.push([key, url]);
        }
      }
       if ('group' in data && data.group.type === 'intensive') {
         if (!tmpGroup.hasOwnProperty(data.group.name)) {
           tmpGroup[data.group.name] = [];
         }
         tmpGroup[data.group.name].push([data.group.index, key]);
       }
    }

    for (const groupName in tmpGroup) {
      const sorted = tmpGroup[groupName].sort((a, b) => a[0] - b[0]);
      $formant.selectState.group[groupName] = sorted.map( x => x[1]); // remove sort index
    }

    const results = await Promise.all(urls.map(async ([key, url]) => {
      // init select2 options
      $formant.selectState.loading[key] = true;
      let results = await fetchData(url);
      $formant.selectState.option[key] = results.data;
      $formant.selectState.loading[key] = false;
    }));

    formant.searchFromSearchParams();

  }; // end of init

  const onSelect2 = async (key, value, label) => {
    formant.addFilterWithFunnel({
      [key]: {
        value: value,
        display: label,
        name: key,
      }
    });
  }

  const onSelect2Clear = (key) => {
    formant.removeFilterWithFunnel(key);
  };

  const handleSelectContinent = async (e) => {
    let url = `api/v1/named-areas`;
    let filter = {
      area_class_id: 7,
      continent: e.target.value,
    };
    url = `${$HOST}/${url}?filter=${JSON.stringify(filter)}`;
    let results = await fetchData(url);
    $formant.selectState.option.country = results.data;
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

    formant.goSearch();
  }

  const onScientificNameSelect = (selected) => {
    // formant.removeFilter('scientific_name');
    // let rank = selected.rank;
    // let label = selected.display_name;
    //   formant.addFilter({
    //     [rank]: {
    //       value: selected.id,
    //       display: label,
    //       name: rank,
    //     }
    //   });
    //goSearch();
    //console.log(rank, selected.id, label);
    formant.addFilter({
      scientific_name: {
        value: selected.id,
        display: selected.display_name,
        name: 'scientific_name',
      }
  });

  };

  const onScientificNameInput = async (input) => {
    if (input && input.length >= 2) {
      $formant.selectState.loading.scientific_name = true;
      let url = '';
      if (input.length >= 4) {
        url = `${$HOST}/api/v1/taxa?filter={"q":"${input}"}`;
      } else {
        url = `${$HOST}/api/v1/taxa?filter={"q":"${input}"}&range=[0, 100]`;
      }
      let results = await fetchData(url);
      if (results.data) {
        $formant.selectState.option.scientific_name = results.data;
      }
    }
  }

  onMount(async () => {
    init();
  });
  //$:{ console.log('select2State: ', select2State); }

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
      <button class="uk-button uk-button-secondary uk-button-small" type="button" on:click={() => { formant.resetForm(); }}>清除</button>
      <button class="uk-button uk-button-primary uk-button-small" type="submit">送出</button>
    </div>
    <fieldset class="uk-fieldset">
      <h5 class="uk-heading-line uk-text-center uk-text-muted filter-title"><span>物種</span></h5>
      <FormWidget>
        <svelte:fragment slot="label">學名</svelte:fragment>
        <svelte:fragment slot="control">
          <Select2
            options={$formant.selectState.option.scientific_name}
            optionText="display_name"
            optionValue="id"
            onCallbackFetch={(x) => onScientificNameSelect(x)}
            onCallbackClear={ () => onSelect2Clear('scientific_name')}
            value={$formant.formValues.scientific_name}
            onInput={onScientificNameInput}
            displayValue={$formant.formValues.scientific_name?.display}
            />
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">科名 (Family)</svelte:fragment>
        <svelte:fragment slot="control">
          {#if $formant.selectState.loading.family === false}
            <Select2 options={$formant.selectState.option.family} optionText="display_name" optionValue="id" onCallback={(x, y) => onSelect2('family', x, y)} onCallbackClear={ () => onSelect2Clear('family')} value={$formant.formValues.family} displayValue={$formant.formValues.family?.display}/>
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">屬名 (Genus)</svelte:fragment>
        <svelte:fragment slot="control">
          {#if $formant.selectState.loading.genus === false}
            <Select2 options={$formant.selectState.option.genus} optionText="display_name" optionValue="id" disabled={($formant.selectState.option.genus && $formant.selectState.option.genus.length > 0) ? false : true} onCallback={(x, y) => onSelect2('genus', x , y)} onCallbackClear={ () => onSelect2Clear('genus')} value={$formant.formValues.genus} displayValue={$formant.formValues.genus?.display}/>
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">種名 (Species)</svelte:fragment>
        <svelte:fragment slot="control">
          {#if $formant.selectState.loading.species === false}
            <Select2 options={$formant.selectState.option.species} optionText="display_name" optionValue="id" disabled={($formant.selectState.option.species && $formant.selectState.option.species.length > 0) ? false : true} onCallback={(x, y) => onSelect2('species', x, y)} onCallbackClear={ () => onSelect2Clear('species')} value={$formant.formValues.species} displayValue={$formant.formValues.species?.display}/>
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
          <Select2 options={$formant.selectState.option.collector} optionText="display_name" optionValue="id" onCallback={ (x, y) => onSelect2('collector', x, y)} onCallbackClear={ x => onSelect2Clear('collector')} value={$formant.formValues.collector} displayValue={$formant.formValues.collector?.display} />
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">採集號</svelte:fragment>
        <svelte:fragment slot="control">
          <div class="uk-flex uk-flex-row uk-width-1-1">
            <input class="uk-input uk-margin-small-right" bind:value={$formant.formValues.field_number} />
            <span class="en-dash">-</span>
            <input class="uk-input uk-margin-small-left" bind:value={$formant.formValues.field_number2}/>
          </div>
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">採集日期</svelte:fragment>
        <svelte:fragment slot="control">
          <div uk-grid>
            <div class="uk-width-1-1">
              <input class="uk-input" type="date" bind:value={$formant.formValues.collect_date} />
              <div class="uk-text-center">~</div>
              <input class="uk-input" type="date" bind:value={$formant.formValues.collect_date2}/>
            </div>
          </div>
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">採集月份</svelte:fragment>
        <svelte:fragment slot="control">
              <select class="uk-select" bind:value={$formant.formValues.collect_month}>
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
          <select class="uk-select" on:change={handleSelectContinent} bind:value={$formant.formValues.continent}>
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
          {#if $formant.selectState.loading.country === false}
            <Select2 options={$formant.selectState.option.country} optionText="display_name" optionValue="id" onCallback={(x, y) => onSelect2('country', x, y)} onCallbackClear={ () => onSelect2Clear('country')} value={$formant.formValues.country} />
          {:else}
            <div uk-spinner></div>
              {/if}
            </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">行政區1</svelte:fragment>
        <svelte:fragment slot="control">
          {#if $formant.selectState.loading.adm1 === false}
            <Select2 options={$formant.selectState.option.adm1} optionText="display_name" optionValue="id" onCallback={(x, y) => onSelect2('adm1', x, y)} onCallbackClear={ () => onSelect2Clear('country')} value={$formant.formValues.adm1} />
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">行政區2</svelte:fragment>
        <svelte:fragment slot="control">
          {#if $formant.selectState.loading.adm2 === false}
            <Select2 options={$formant.selectState.option.adm2} optionText="display_name" optionValue="id" onCallback={(x, y) => onSelect2('adm2', x, y)} onCallbackClear={ () => onSelect2Clear('country')} value={$formant.formValues.adm2} />
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">行政區3</svelte:fragment>
        <svelte:fragment slot="control">
          {#if $formant.selectState.loading.adm3 === false}
            <Select2 options={$formant.selectState.option.adm3} optionText="display_name" optionValue="id" onCallback={(x, y) => onSelect2('adm3', x, y)} onCallbackClear={ () => onSelect2Clear('country')} value={$formant.formValues.adm3} />
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">國家公園/保護留區</svelte:fragment>
        <svelte:fragment slot="control">
          {#if $formant.selectState.loading.named_area__park === false}
            <Select2 options={$formant.selectState.option.named_area__park} optionText="display_name" optionValue="id" onCallback={(x, y) => onSelect2('named_area__park', x, y)} onCallbackClear={ () => onSelect2Clear('named_area__park')} value={$formant.formValues.named_area__park} />
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">地點名稱</svelte:fragment>
        <svelte:fragment slot="control">
          {#if $formant.selectState.loading.named_area__locality === false}
            <Select2 options={$formant.selectState.option.named_area__locality} optionText="display_name" optionValue="id" onCallback={(x, y) => onSelect2('named_area__locality', x, y)} onCallbackClear={ () => onSelect2Clear('named_area__locality')} value={$formant.formValues.named_area__locality} />
          {:else}
            <div uk-spinner></div>
          {/if}
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">海拔</svelte:fragment>
        <svelte:fragment slot="control">
          <div class="uk-flex uk-flex-row uk-width-1-1">
            <select class="uk-select uk-margin-small-right" bind:value={$formant.formValues.altitude_condiction}>
              <option value="">-- 選擇 --</option>
              <option value="between">介於</option>
              <option value="gte">大於</option>
              <option value="lte">小於</option>
              <option value="eq">等於</option>
            </select>
            <input class="uk-input uk-margin-small-right" type="text" bind:value={$formant.formValues.altitude}/>
            <span class="en-dash">-</span>
            <input class="uk-input uk-margin-small-left" type="text" bind:value={$formant.formValues.altitude2}/>
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
            <input class="uk-input uk-margin-small-right" type="text" bind:value={$formant.formValues.accession_number}/>
            <span class="en-dash">-</span>
            <input class="uk-input uk-margin-small-left" type="text" bind:value={$formant.formValues.accession_number2}/>
          </div>
        </svelte:fragment>
      </FormWidget>
      <FormWidget>
        <svelte:fragment slot="label">模式標本</svelte:fragment>
        <svelte:fragment slot="control">
          <select class="uk-select" bind:value={$formant.formValues.type_status}>
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
