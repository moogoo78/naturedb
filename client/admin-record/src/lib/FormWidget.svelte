<script>
  import Select2Free from './Select2Free.svelte';

  export let type = '';
  export let label = '';
  export let id = '';
  export let value = '';
  export let placeholder = '';
  export let input = null;
  export let options = [];
  export let checked = false;
  export let initValue = '';
  export let detectTouch = true;

  let touched = false;
  $: if (detectTouch) {
    if (initValue !== value) {
      //console.log(label, id, initValue, value);
      touched = true;
    } else {
      touched = false;
    }
  }
</script>
<div class="widget-container uk-grid-small" uk-grid>
  {#if $$slots.label}
    <slot name="label">
      LABEL
    </slot>
  {:else}
    <label class="uk-width-auto" for={id}>{label}</label>
  {/if}
    <div class="uk-width-expand">
      {#if $$slots.control}
        <slot name="control">Control</slot>
      {:else if type === "input-text"}
        <input type="text" id={id} class="uk-input uk-form-small" placeholder={placeholder} bind:value={value} on:input={input} class:uk-form-success={touched} />
      {:else if type === "input-date"}
        <input type="date" id={id} class="uk-input uk-form-small" bind:value={value} class:uk-form-success={touched} />
      {:else if type === "input-checkbox"}
        <input type="checkbox" id={id} class="uk-checkbox" value={value} bind:checked={checked} class:uk-form-success={touched}/>
      {:else if type === "textarea"}
        <textarea id={id} class="uk-textarea uk-form-small" bind:value={value} class:uk-form-success={touched} />
      {:else if type === "select"}
        <select id={id} class="uk-select uk-form-small" bind:value={value} class:uk-form-success={touched}>
          <option value="">-- 選擇 --</option>
          {#each options as option}
            <option value={option.value}>{option.text}</option>
          {/each}
        </select>
      {:else if type === "free"}
        <Select2Free
          bind:value={value}
          options={options}
          initValue={initValue}
          />
      {/if}
    </div>
  {#if $$slots.label2}
    <slot name="label2">
      <label class="uk-width-auto" for={id}>label</label>
    </slot>
  {/if}

</div>

<style>
  .widget-container {
    margin: 2px 0;
  }
  .my-form-label {
    margin-top: 7px;
    float: left;
    width: 80px;
  }
  .my-form-control {
    margin-left: 80px;
  }
</style>
