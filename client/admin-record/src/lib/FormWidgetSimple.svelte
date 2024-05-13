<script>
  export let value = '';
  export let type = '';
  export let initValue = '';
  let touched = false;
  $: if (initValue !== value) {
    //console.log(label, id, initValue, value);
    touched = true;
  } else {
    touched = false;
  }
</script>

{#if type === "input-text"}
  <input class="uk-input uk-form-small mg-input-xsmall" bind:value={value} type="text" class:uk-form-success={touched} />
{:else if type === "input-number"}
  <input class="uk-input uk-form-small mg-input-xsmall" bind:value={value} type="number" class:uk-form-success={touched} />
{/if}
