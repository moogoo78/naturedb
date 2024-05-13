<!--
    via: https://svelte.dev/repl/5734f123973d4682978427024ca90850?version=3.29.0
    modified: match string: startsWith => includes
-->
<script>
  import { values } from '../stores.js';
  import { filterItems, removeHTML, fetchData } from '../utils.js';

  export let value = null;
  export let options = []; // {text: 'foo', value: 'bar'}
  export let disabled = false;
  export let onSelect = null;
  export let onClear = null;
  export let onInput = null;
  export let initValue = null;

  let touched = false;
  let boxSearchInput; // use with bind:this to focus element
  // let boxSearchValue; // 會慢一步, render 順序?
  let boxSearchContainer;
  let isBoxOpen = false;
  let filtered = [];

  $: if (!value) {
    filtered = [];
    value = {text: ''};
  }

  $: sorted: filtered.sort((a, b) => {
    let x = a.text.toLowerCase();
    let y = b.text.toLowerCase();
    if( x > y ) {
      return 1;
    }
    if( x < y ){
      return -1;
    }
    return 0;
  });

  $: if (initValue && initValue !== value.value) {
    touched = true;
  } else {
    touched = false;
    if (!initValue && value.text) {
      touched = true;
    }
  }

  const handleBoxSelect = (selected) => {
    //consoel.log(selected);
    let text = selected.text;
    const foundIndex = options.findIndex((option) => option.value === selected.value);
    if (foundIndex >= 0) {
      value = {...selected};
      if (onSelect) {
        onSelect(selected);
      }
      isBoxOpen = false;
      closeBox();
    } else {
      console.error('not found clicked option');
    }
  }

  /* NAVIGATING OVER THE LIST OF COUNTRIES W HIGHLIGHTING */
  //$: console.log(hiLiteIndex);
  //$: hiLitedCountry = filtered[selected];

  const closeBox = () => {
    filtered = [];
    boxSearchInput.blur();
    boxSearchContainer.style.display = 'none';
  }

  const toggleBox = (e) => {
    e.preventDefault();
    e.stopPropagation();

    isBoxOpen = !isBoxOpen;
    if (isBoxOpen === true) {
      filtered = [...options];
      boxSearchContainer.style.display = 'block';
      boxSearchInput.focus();
    } else {
      closeBox()
    }
  }

  const handleInput = async (e) => {
    if (onInput) {
      await onInput(e.target.value);
    }
    filtered = filterItems(e.target.value, options);
  }

  const handleClear = () => {
    value = null;
    if (onClear) {
      onClear();
    }
  }
</script>
<div class="select2-container">
  <div class="uk-inline uk-width">
    {#if value}
      <a class="uk-form-icon uk-form-icon-flip" on:click={handleClear} uk-icon="icon: close"></a>
    {:else}
      <a class="uk-form-icon uk-form-icon-flip" on:click={toggleBox} uk-icon="icon: {(isBoxOpen) ? 'chevron-up' : 'chevron-down'}"></a>
    {/if}
      <input class="uk-input uk-form-small" type="text" placeholder="-- 選擇 --" on:click={toggleBox} disabled={disabled} bind:value={value.text} readonly class:uk-form-success={touched} />
    </div>
  <div class="uk-inline box-search-container" bind:this={boxSearchContainer}>
    <span class="uk-form-icon" uk-icon="icon: search"></span>
    <input class="uk-input uk-form-small" bind:this={boxSearchInput} on:input={handleInput} />
  </div>
  {#if filtered.length > 0}
    <ul class="box-items-list">
      {#each filtered as option}
        <li class="box-items {(option.value===value.value) ? 'active' : ''}" on:click={() => handleBoxSelect(option)}>{#if option.styled}{@html option.styled}{:else}{option.text}{/if}</li>
      {/each}
    </ul>
  {/if}
</div>


<style>
  .select2-container {
    width: 100%;
  }
  .box-search-container {
    margin-top: 0px;
    display: none;
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
    max-height: 340px;
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
    padding: 6px;
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
