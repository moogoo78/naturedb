<script>
  import { HOST, searching, unitResults, filterTags, pagination, formValues, isLanding } from './stores.js';
  import Sidebar from './Sidebar.svelte';
  import Searchbar from './Searchbar.svelte';
  import Main from './Main.svelte';
  import { fetchData } from './utils.js';
  //import SearchbarResults from './SearchbarResults.svelte';

  let isSidebarOpen = true;

  const removeFilter = (key, tag) => {
    let values = {...$formValues};
    let k = key;
    if (typeof tag.value === 'object') {
      k = tag.value.name;
      // delete related
      if (['family', 'genus', 'species'].indexOf(k) >= 0) {
        for (let i of ['family', 'genus', 'species']) {
          delete values[i];
        }
      }
    }
    delete values[k];
    formValues.set(values);
    goSearch();
  }

  const goSearch = (args) => {
    let isPageChanged = false;
    let payload = {
      filter: {},
      range: [0, 20],
    };
    if (args && args.range && args.range.length >=2) {
      isPageChanged = true;
      payload = {
        ...payload,
        range: args.range,
      }
    }
    // tags to filter
    for (const key in $filterTags) {
      payload.filter[key] = (typeof $filterTags[key].value === 'object') ? $filterTags[key].value.value : $filterTags[key].value;
    }

    let params = [];
    for (const key in payload) {
      params.push(`${key}=${JSON.stringify(payload[key])}`);
    }

    let queryString = params.join('&');
    let url = `${$HOST}/api/v1/search?${queryString}`;
    searching.set(true);
    //isOpen = false;
    fetchData(url, (results)=> {
      console.log('<Main>: search)', results);
      unitResults.set(results);
      if (!isPageChanged) {
        pagination.set({
          page: 0,
          perPage: 20,
          count: results.total,
        });
      }
      searching.set(false);
    });
  };

  const toggleSidebarOpen = () => {
    isSidebarOpen = !isSidebarOpen
  }
  </script>

<div class="uk-container{($isLanding) ? ' uk-container-small' : ''}">
  <div class="uk-child-width-expand uk-grid-small" uk-grid>
    <!-- <div class="uk-width-1-1"> -->
      <!-- <Searchbar /> -->
      <!-- </div> -->
    <div class="{($isLanding) ? 'uk-width-1-1' : 'uk-width-1-4'}{(isSidebarOpen) ? '' : ' uk-hidden'}">
      <Sidebar goSearch={goSearch} toggleOpen={toggleSidebarOpen}/>
    </div>
    <div class="uk-card uk-card-default uk-card-small uk-card-body uk-width-expand{($isLanding) ? ' uk-hidden' : ''}">
      {#if !isSidebarOpen}
        <div class="uk-text-muted" on:click|preventDefault={toggleSidebarOpen}>&lt;&lt; 打開篩選條件</div>
      {/if}
      {#if $searching}
        <div class="uk-flex uk-flex-center" id="overlay-spinner">
          <div uk-spinner="ratio: 1.8"></div>
        </div>
      {:else}
        {#if $unitResults && $unitResults.data}
          <Main removeFilter={removeFilter} goSearch={goSearch} />
        {/if}
      {/if}
    </div>
  </div>
</div>
<!-- <form> -->
  <!-- <ul class="uk-subnav uk-subnav-pill" uk-switcher> -->
  <!--   <li><a href="#">全文搜尋</a></li> -->
  <!--   <li>條件篩選</li> -->
  <!-- </ul> -->

  <!-- <ul class="uk-switcher uk-margin"> -->
  <!--   <li> -->
  <!--     <Searchbar /> -->
  <!--     <SearchbarResults /> -->
  <!--   </li> -->
  <!--   <li><SearchFilter /></li> -->
    <!-- </ul> -->
  <!-- <SearchFilter /> -->
<!-- </form> -->
<style>
  #overlay {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    background-color:#000;
    opacity: .75;
    z-index: 9999999;
  }
</style>
