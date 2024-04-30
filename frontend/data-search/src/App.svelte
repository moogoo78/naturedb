<script>
  import { formant } from './stores.js';
  import Filter from './lib/Filter.svelte';
  import Result from './lib/Result.svelte';
  //import SearchbarResults from './SearchbarResults.svelte';

  let isLanding = true;
  let isSidebarOpen = true;

  const toggleSidebarOpen = () => {
    isSidebarOpen = !isSidebarOpen;
  }

  $: { console.log('[formant]', $formant);}
</script>

<div class="uk-container{(isLanding) ? ' uk-container-small' : ''}">
  <div class="uk-child-width-expand uk-grid-small" uk-grid>
    <!-- <div class="uk-width-1-1"> -->
      <!-- <Searchbar /> -->
      <!-- </div> -->
    <div class="{(isLanding) ? 'uk-width-1-1' : 'uk-width-1-4'}{(isSidebarOpen) ? '' : ' uk-hidden'}">
      <Filter bind:isSidebarOpen bind:isLanding />
    </div>
    <div class="uk-card uk-card-default uk-card-small uk-card-body uk-width-expand{(isLanding) ? ' uk-hidden' : ''}">
      {#if !isSidebarOpen}
        <div class="uk-text-muted" on:click|preventDefault={toggleSidebarOpen}>&lt;&lt; 打開篩選條件</div>
      {/if}
      {#if $formant.searching}
        <div class="uk-flex uk-flex-center" id="overlay-spinner">
          <div uk-spinner="ratio: 1.8"></div>
        </div>
      {:else}
        {#if $formant.error}
          Error: {$formant.error}
        {:else}
          <Result results={$formant.results} />
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
