<script>
  import { register } from './stores.js';
  import { formant } from './formant.js';

  const handleRemove = (param, tag) => {
    console.log(tag);
    let funnel = formant.findFunnel(tag.key);
    if (funnel) {
      formant.removeFilter(funnel);
    } else {
      formant.removeFilter(tag.key);
    }
    formant.goSearch();
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
          <button class="uk-margin-left" type="button" uk-close on:click|preventDefault={() => { handleRemove(key, tag);}}></button>
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
