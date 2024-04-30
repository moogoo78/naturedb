<script>
  import { HOST, ftsResults } from './stores.js';
  import { fetchData } from './utils.js';

  let alphaCategories = [
    {
      name: 'scientificName',
      label: '學名',
    }, {
      name: 'person',
      label: '人名',
    }, {
      name: 'namedArea',
      label: '地名',
    }];
  let digitCategories = [
    {
      name: 'fieldNumber',
      label: '採集號',
    }, {
      name: 'accessionNmuber',
      label: '館號',
    }];

  let q;
  let filtered = [];

  const onSubmit = () => {
    let url = `${$HOST}/api/v1/searchbar?q=${q}`;
    searching.set(true);
    fetchData(url, (results)=> {
      ftsResults.set(results);
      searching.set(false);
    });
  };

  function _isOnlyDigits(str) {
    return /^\d+$/.test(str);
  }

  const handleInput = (e) => {
    filtered = [];
    if (_isOnlyDigits(q)) {
      for (let i in digitCategories) {
        filtered.push([
          digitCategories[i].name,
          `搜尋<strong>${digitCategories[i].label}</strong>: ${q}`
        ]);
      }
    } else {
      for (let i in alphaCategories) {
        filtered.push([
          alphaCategories[i].name,
          `搜尋<strong>${alphaCategories[i].label}</strong>: ${q}`
        ]);
      }
      for (let i in digitCategories) {
        filtered.push([
          digitCategories[i].name,
          `搜尋<strong>${digitCategories[i].label}</strong>: ${q}`
        ]);
      }
    }
  }

  const handleBoxSelect = (name) => {
    //console.log(filtered[index]);
    console.log(name, q);
  }
</script>

<div class="uk-grid-small uk-margin" uk-grid>
  <div class="uk-width-expand">
    <div class="uk-inline uk-width-expand">
      <span class="uk-form-icon" uk-icon="icon: search"></span>
      <input id="data-search-searchbar-input" type="search" name="text_search" class="search-input uk-input uk-form-large" autocapitalize="none" autocorrect="off" autocomplete="off" placeholder="學名、人名、地名、採集號、館號" bind:value={q} on:input={handleInput}/>
    </div>
    <div class="uk-inline box-search-container">
      {#if filtered.length > 0}
        <ul class="box-items-list">
          {#each filtered as item}
            <li class="box-items" on:click={()=> handleBoxSelect(item[0])}>{@html item[1]}</li>
          {/each}
        </ul>
      {/if}
    </div>
  </div>
  <div class="uk-width-auto">
    <button class="uk-button uk-button-primary uk-form-large" type="button" on:click|preventDefault={onSubmit}>搜尋</button>
  </div>
</div>


<style>
  .box-search-container {
    margin-top: 4px;
    display: block;
  }
  .box-search-container input {
    background-color: #eee;
    /*border-radius:10px 10px 0px 0px;*/
  }
  .box-items-list {
    position: relative;
    margin: 0;
    padding: 0;
    top: 0;
    width: 100%;
    border: 1px solid #ddd;
    background-color: #ddd;
    max-height: 230px;
    overflow-y: scroll;
  }
  li.box-items {
    list-style: none;
    /*border-bottom: 1px solid #d4d4d4;*/
    z-index: 99;
    /*position the autocomplete items to be the same width as the container:*/
    top: 100%;
    left: 0;
    right: 0;
    padding: 10px;
    cursor: pointer;
    background-color: #fff;
  }
  li.box-items:hover {
    /*when hovering an item:*/
    background-color: #eee;
  }

  li.box-items.active {
    color: blue;
    background-color: #eee;
  }
</style>
