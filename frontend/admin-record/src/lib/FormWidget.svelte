<script>
  export let type = '';
  export let label = '';
  export let id = '';
  export let value = '';
  export let placeholder = '';
  export let input = null;
  export let options = [];
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
        <input type="text" id={id} class="uk-input uk-form-small" placeholder={placeholder} bind:value={value} on:input={input} />
      {:else if type === "input-date"}
        <input type="date" id={id} class="uk-input uk-form-small" bind:value={value} />
      {:else if type === "textarea"}
        <textarea id={id} class="uk-textarea uk-form-small" bind:value={value} />
      {:else if type === "select"}
        <select id={id} class="uk-select uk-form-small" bind:value={value}>
          <option value="">-- 選擇 --</option>
          {#each options as option}
            <option value={option.value}>{option.text}</option>
          {/each}
        </select>
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
