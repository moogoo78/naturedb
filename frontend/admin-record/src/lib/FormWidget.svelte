<script>
  export let type = '';
  export let label = '';
  export let id = '';
  export let value = '';
  export let placeholder = '';
  export let input = null;
</script>
<div class="widget-container uk-grid-small" uk-grid>
  {#if $$slots.label}
    <slot name="label">
      <label class="uk-width-auto" for={id}>label</label>
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
        <input type="date" id={id} class="uk-input uk-form-small" value={value} />
      {:else if type === "textarea-read"}
        <textarea id={id} class="uk-textarea uk-form-small">{value}</textarea>
      {/if}
    </div>
  {#if $$slots.label2}
    <slot name="label2">
      <label class="uk-width-auto" for={id}>label</label>
    </slot>
  {/if}

</div>

<style>
  * + .widget-container {
    margin-top: 4px;
  }
  .widget-container {
    margin-bottom: 4px;
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
