<script>
  import { register, formant, formValues } from '../stores.js';

  const removeFilter = (key, tag) => {
    let values = {...$formValues};
    let k = key;
    if (typeof tag.value === 'object') {
      k = tag.value.name;
      // delete related
      if (key === 'taxon_id') {
        if (['family', 'genus', 'species'].indexOf(k) >= 0) {
          for (let i of ['family', 'genus', 'species']) {
            delete values[i];
          }
        }
      } else if (key === 'named_area__admin') {
        delete values.adm1;
        delete values.adm2;
        delete values.adm3;
      } else if ($register[key].group && $register[key].group.type === 'extensive') {
        delete values[key];
        let extTo = $register[key].group.to;
        if (values[extTo]) {
          delete values[extTo];
        }
      }
    }
    delete values[k];

    formValues.set(values);
    formant.update( pv => {
      let payloadFilter = {...pv.payload.filter};
      delete payloadFilter[key];
      return {
        ...pv,
        payload: {
          ...pv.payload,
          filter: payloadFilter,
        }
      }
    });
    formant.goSearch({formValues: values});
  }
</script>
<div id="search-tag-container" class="uk-container uk-grid-small" uk-grid>
  {#each Object.entries($formant.tags) as [key, tag]}
    <div>
      <div class="uk-card uk-border-rounded search-tag-box">
        <div class="uk-flex uk-flex-middle">
          <div>
            <div><span class="uk-text-bold">{tag.label}</span>: { (typeof tag.value === 'object') ? tag.value.display : tag.value }</div>
          </div>
          <button class="uk-margin-left" type="button" uk-close on:click|preventDefault={() => removeFilter(key, tag)}></button>
        </div>
      </div>
    </div>
  {/each}
</div>

<style>
  /* #search-tag-container { */
  /*   padding: 20px; */
  /*   background-color: #f4f4f4; */
  /*   border: 1px solid #eee; */
  /*   border-radius: 4px; */
  /* } */
  .search-tag-box {
    border: 1px solid #bfbfbf;
    padding: 4px 20px;
    background: #f4fafb;
  }
</style>
