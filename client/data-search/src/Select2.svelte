<!--
    via: https://svelte.dev/repl/5734f123973d4682978427024ca90850?version=3.29.0
    modified: match string: startsWith => includes
-->
<script>
  export let value = '';
  export let options = [];
  export let optionText = 'display_name';
  export let optionValue = 'id';
  export let disabled = false;
  export let onCallback = null;
  export let onCallbackFetch = null;
  export let onCallbackClear = null;
  export let onInput = null;
  export let displayValue = '';

  import {filterItems, removeHTML} from './utils.js';

  let boxSearchInput; // use with bind:this to focus element
  // let boxSearchValue; // 會慢一步, render 順序?
  let boxSearchContainer;
  let isBoxOpen = false;
  let filtered = [];
  let selectedIndex = null;

  $: if (!displayValue) {
    filtered = [];
    selectedIndex = null;
  }
  $: if (!value) {
    filtered = [];
    selectedIndex = null;
    displayValue = '';
  }

  $: sortedItems = filtered.sort();

  const handleBoxSelect = (index) => {
    let text = removeHTML(filtered[index]);
    const foundIndex = options.findIndex((option) => option[optionText] === text);
    if (foundIndex >=0) {
      let selectedText = options[foundIndex][optionText];
      value = options[foundIndex][optionValue];
      selectedIndex = foundIndex;

      displayValue = removeHTML(selectedText);

      if (onCallback) {
        onCallback(value, displayValue);
      }

      isBoxOpen = false;
      closeBox();
      //document.querySelector(`#${id}__control`).focus();
    } else {
      console.error('not found clicked option');
    }
  }

  const handleBoxSelectFetch = (selected) => {
    let text = removeHTML(selected);
    displayValue = text;
    const foundIndex = options.findIndex((option) => option[optionText] === text);
    if (foundIndex >= 0) {
      onCallbackFetch(options[foundIndex]);
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
      filtered = options.map(option => {
        return option[optionText];
      });
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
    filtered = filterItems(e.target.value, options, optionText);
  }
</script>


<div class="select2-container">
  <div class="uk-inline uk-width">
    {#if value}
      <a class="uk-form-icon uk-form-icon-flip" on:click={onCallbackClear} uk-icon="icon: close"></a>
    {:else}
      <a class="uk-form-icon uk-form-icon-flip" on:click={toggleBox} uk-icon="icon: {(isBoxOpen) ? 'chevron-up' : 'chevron-down'}"></a>
    {/if}
      <input class="uk-input" type="text" placeholder="-- 選擇 --" on:click={toggleBox} disabled={disabled} bind:value={displayValue} readonly/>
    </div>
  <!-- other style: dropdown button -->
  <!-- <div class="uk-button-group uk-width-1-1"> -->
  <!--   <button class="uk-button uk-button-default uk-width-expand" disabled={disabled}  on:click|preventDefault={toggleBox}>{displayValue || "-- 選擇 --"}</button> -->
  <!--   <div class="uk-inline"> -->
  <!--     <button class="uk-button uk-button-default" type="button" aria-label="Toggle Dropdown" on:click|preventDefault={toggleBox}><span uk-icon="icon: {(isBoxOpen) ? 'triangle-up' : 'triangle-down'}"></span></button> -->
  <!--   </div> -->
  <!-- </div> -->
  <!-- other style: input -->
  <!-- <div class="uk-inline uk-width">   -->
    <!-- <a class="uk-form-icon uk-form-icon-flip" on:click={toggleBox} uk-icon="icon: {(isBoxOpen) ? 'chevron-up' : 'chevron-down'}"></a> -->
    <!--   <input class="uk-input" type="text" placeholder="-- 選擇 --" on:click={toggleBox} disabled={disabled} bind:value={displayValue} bind:this={displayInput}/> -->
    <!-- </div> -->

  <!-- bind:value={boxSearchValue} -->
  <div class="uk-inline box-search-container" bind:this={boxSearchContainer}>
    <span class="uk-form-icon" uk-icon="icon: search"></span>
    <input class="uk-input" bind:this={boxSearchInput} on:input={handleInput} />
  </div>
  {#if sortedItems.length > 0}
    <ul class="box-items-list">
      {#each sortedItems as text, i}
        {#if onCallbackFetch}
          <li class="box-items{(i===selectedIndex) ? ' active':''}" on:click={() => handleBoxSelectFetch(text)}>{@html text}</li>
        {:else}
          <li class="box-items{(i===selectedIndex) ? ' active':''}" on:click={() => handleBoxSelect(i)}>{@html text}</li>
        {/if}
      {/each}
    </ul>
  {/if}
</div>

<style>
  .select2-container {
    width: 100%;
  }
  .box-search-container {
    margin-top: 4px;
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
    max-height: 200px;
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
