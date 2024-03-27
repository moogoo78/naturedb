<script>
  import { unitResults, filterTags, pagination } from './stores.js';
  import UnitTable from './UnitTable.svelte';
  import Pagination from './Pagination.svelte';

  export let goSearch;
  export let removeFilter;
</script>

<h4 class="uk-text-primary">搜尋結果</h4>
<div class="uk-flex uk-flex-between">
  <div>
    <div class="uk-text">標本數:{$unitResults.total}
      <span class="uk-text-small uk-article-meta">(時間:{Number.parseFloat($unitResults.elapsed).toFixed(2)}秒)</span>
    </div>
  </div>
  <div>
    <!-- BEGIN: sort by-->
    <ul class="uk-subnav uk-subnav-pill" uk-margin>
      <li>
        <a href="#"><span id="sort-label">採集號(小到大)</span><span uk-icon="icon: triangle-down"></span></a>
        <div uk-dropdown="mode: click" id="sort-select">
          <ul class="uk-nav uk-dropdown-nav">
            <li class="uk-active"><a href="#" class="sort-nav" data-sort="field_number" data-desc="1">採集號(大到小)</a></li>
            <li class="uk-active"><a href="#" class="sort-nav" data-sort="field_number" data-desc="0">採集號(小到大)</a></li>
            <li class="uk-active"><a href="#" class="sort-nav" data-sort="collect_date" data-desc="1">採集日期(新到舊)</a></li>
            <li class="uk-active"><a href="#" class="sort-nav" data-sort="collect_date" data-desc="0">採集日期(舊到新)</a></li>
            <li class="uk-active"><a href="#" class="sort-nav" data-sort="accession_number" data-desc="1">館號(大到小)</a></li>
            <li class="uk-active"><a href="#" class="sort-nav" data-sort="accession_number" data-desc="0">館號(小到大)</a></li>
          </ul>
        </div>
      </li>
    </ul>
    <!-- END: sort by-->
  </div>
</div>

<div id="search-tag-container" class="uk-container uk-grid-small" uk-grid>
  {#each Object.entries($filterTags) as [key, tag]}
    <div>
      <div class="uk-card uk-border-rounded search-tag-box">
        <div class="uk-flex uk-flex-middle">
          <div>
            <div><span class="uk-text-bold">{tag.label}</span>: { (typeof tag.value === 'object') ? tag.value.display : tag.value }</div>
          </div>
          <button class="uk-margin-left" type="button" uk-close on:click|preventDefault={() => removeFilter(key, tag)}></button>
        </div>
      </div>
    </div>
  {/each}
</div>

<ul uk-tab id="search-result-view-tab">
  <li class="uk-active" data-view="table" data-tab="0"><a href="#">表格</a></li>
  <li data-view="list" data-tab="1"><a href="#">條列</a></li>
  <!-- <li><a href="#" data-view="gallery">照片</a></li> -->
  <li data-view="map" data-tab="2"><a href="#" >地圖</a></li>
  <!--<li data-view="checklist" data-tab="3"><a href="#">物種名錄</a></li>-->
</ul>

<UnitTable rows={$unitResults.data}/>

<Pagination toPageCallback={(range) => goSearch({range:range})}/>
<style>
  /* #search-tag-container { */
  /*   padding: 20px; */
  /*   background-color: #f4f4f4; */
  /*   border: 1px solid #eee; */
  /*   border-radius: 4px; */
  /* } */
  .search-tag-box {
    border: 1px solid #bfbfbf;
    padding: 4px 20px;
    background: #d9d9d9;
  }
</style>
