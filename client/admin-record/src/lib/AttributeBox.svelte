<script>
  /*import Select2a from './Select2a.svelte'*/
  import FormWidget from './FormWidget.svelte';

  export let attrTypes = [];
  export let values = {};
  export let optionKey = {
    value: 'id',
    text: 'display_name,'
  };
  export let initValues = {};
</script>

{#each attrTypes as atype}
  {#if atype.input_type === "select"}
    <FormWidget id="" bind:value={values[atype.name]} label={atype.label} type="select" options={atype.options.map( x => {
      if (Array.isArray(x) && x.length) {
        return {text: x[1], value: x[0]};
      } else {
        return {text: x[optionKey.text], value: x[optionKey.value]};
      }
      })} detectTouch={false} />
  {:else if atype.input_type === "free"}
    <FormWidget id="" bind:value={values[atype.name]} label={atype.label} type="free" options={atype.options.map( x => {
      if (Array.isArray(x) && x.length) {
        return {text: x[1], value: x[0]};
      } else {
        return {text: x[optionKey.text], value: x[optionKey.value]};
      }
  })} initValue={initValues[atype.name]} />
  {:else if atype.input_type === "input"}
    <FormWidget id="" bind:value={values[atype.name]} label={atype.label} type="input-text" initValue={initValues[atype.name]}></FormWidget>
  {:else if atype.input_type === "checkbox"}
    <FormWidget id="" value="Y" label={atype.label} type="input-checkbox" bind:checked={values[atype.name]} initvalue={initValues[atype.name]}></FormWidget>
  {:else if atype.input_type === "text"}
    <FormWidget id="" bind:value={values[atype.name]} label={atype.label} type="textarea" initValue={initValues[atype.name]}></FormWidget>
  {/if}
{/each}

      <!-- <svelte:fragment slot="label">
      <!--   <label class="uk-width-auto" for="form">{atype.label}</label> -->
      <!-- </svelte:fragment> -->
      <!-- <svelte:fragment slot="control"> -->
      <!--   <Select2a -->
      <!--     options={atype.options.map( x => ({ -->
      <!--       text: x[optionKey.text], -->
      <!--       value: x[optionKey.value] -->
      <!--     }))} -->
      <!--     value={values[atype.name]} -->
      <!--     onSelect={(selected)=>{ -->
      <!--       values[atype.name] = selected; -->
      <!--     }} -->
      <!--     onClear={()=>{values[atype.name]=null;}} -->
      <!--     /> -->
      <!-- </svelte:fragment> -->
