<script>
  import { formant } from './formant.js';
  import FilterTags from './FilterTags.svelte';
  import UnitTable from './UnitTable.svelte';
  import MapView from './MapView.svelte';
  import Pagination from './Pagination.svelte';

  export let results;

  let sortKey = '-field_number';
  let sortLabels = {
    'field_number': '採集號(小到大)',
    '-field_number': '採集號(大到小)',
    '-collect_date': '採集日期(新到舊)',
    'collect_date': '採集日期(舊到新)',
    'accession_number': '館號(小到大)',
    '-accession_number': '館號(大到小)',
  };

  const onSort = (e) => {
    sortKey = e.target.dataset.sort;
    formant.goSearch({sort: sortKey});
  };

  const onView = (e) => {
    formant.goSearch({VIEW: e.target.dataset.view});
  }
</script>

<h4 class="uk-text-primary">搜尋結果</h4>
<div class="uk-flex uk-flex-between">
  <div>
    <div class="uk-text">資料筆數:{results.total}
      <span class="uk-text-small uk-article-meta">(時間:{Number.parseFloat(results.elapsed).toFixed(2)}秒)</span>
    </div>
  </div>
  <div>
    <!-- BEGIN: sort by-->
    <ul class="uk-subnav uk-subnav-pill" uk-margin>
      <li>
        <a href="#"><span id="sort-label">{($formant.payload.sort.length > 0) ? sortLabels[$formant.payload.sort[0]]:sortLabels['-field_number']}</span><span uk-icon="icon: triangle-down"></span></a>
        <div uk-dropdown="mode: click" id="sort-select">
          <ul class="uk-nav uk-dropdown-nav">
            {#each Object.entries(sortLabels) as [key, label]}
              <li class={(sortKey===key) ? "uk-active" : ""}><a href="#" class="sort-nav" data-sort={key} on:click|preventDefault={onSort}>{label}</a></li>
            {/each}
          </ul>
        </div>
      </li>
    </ul>
    <!-- END: sort by-->
  </div>
</div>

<FilterTags  />


<ul uk-tab id="search-result-view-tab">
  <li class:uk-active={$formant.payload.VIEW === 'table'} data-tab="0"><a href="#" data-view="table" on:click|preventDefault={onView}>表格</a></li>
  <!--<li data-view="list" data-tab="1"><a href="#">條列</a></li>-->
  <!-- <li><a href="#" data-view="gallery">照片</a></li> -->
  <li class:uk-active={$formant.payload.VIEW === 'map'} data-tab="2"><a href="#" data-view="map" on:click|preventDefault={onView} >地圖</a></li>
  <!--<li data-view="checklist" data-tab="3"><a href="#">物種名錄</a></li>-->
</ul>

{#if $formant.payload.VIEW === 'table'}
  {#if results.data}
    <UnitTable rows={results.data} start={($formant.pagination.page*$formant.pagination.perPage) + 1}/>
  {/if}
  <Pagination bind:pagination={$formant.pagination} toPageCallback={(page) => formant.goSearch({page:page})}/>
{:else if $formant.payload.VIEW === 'map'}
  {#if results.data}
    <MapView rows={results.data} />
  {:else}
    no data
  {/if}
{/if}

