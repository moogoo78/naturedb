<script>
  import { ftsResults, searching } from './stores.js';
</script>


{#if $ftsResults}
<ul uk-tab>
    <li class="uk-active"><a href="#">學名<span class="uk-badge">{$ftsResults.taxon.length}</span></a></li>
    <li><a href="#">人名<span class="uk-badge">{$ftsResults.person.length}</span></a></li>
    <li><a href="#">地名<span class="uk-badge">{$ftsResults.named_area.length}</span></a></li>
    <li><a href="#">採集號<span class="uk-badge">{$ftsResults.field_number.length}</span></a></li>
    <li><a href="#">館號<span class="uk-badge">{$ftsResults.accession_number.length}</span></a></li>
</ul>

<ul class="uk-switcher uk-margin">
  <li>
    <div class="uk-child-width-1-2@s uk-grid-match" uk-grid>
      {#each $ftsResults.taxon as data, i}
        <div>
          <div class="uk-card uk-card-hover uk-card-default uk-card-small uk-card-body">
            <div class="uk-card-badge uk-label uk-label-success">{data.rank}</div>
            <h3 class="uk-card-title">{data.full_scientific_name}</h3>
            <p>{data.common_name}</p>
            <p><a class="uk-button uk-button-default uk-button-small uk-align-right">標本</a></p>
          </div>
        </div>
      {/each}
    </div>
  </li>
  <li>
    <div class="uk-child-width-1-2@s uk-grid-match" uk-grid>
      {#each $ftsResults.person as data, i}
        <div>
          <div class="uk-card uk-card-hover uk-card-default uk-card-small uk-card-body">
        <div class="uk-card-badge uk-label uk-label-success">{#if data.is_collector}採集者{/if}{#if data.is_identifier} | 鑒定者{/if}</div>
          <h3 class="uk-card-title">{data.display_name}</h3>
        {#if data.abbreviated_name }<p>名字縮寫: {data.abbreviated_name}</p>{/if}
        <p><a class="uk-button uk-button-default uk-button-small uk-align-right">標本</a></p>
          </div>
        </div>
      {/each}
    </div>
  </li>
  <li>
    <div class="uk-child-width-1-2@s uk-grid-match" uk-grid>
      {#each $ftsResults.named_area as data, i}
        <div>
          <div class="uk-card uk-card-hover uk-card-default uk-card-small uk-card-body">
            <h3 class="uk-card-title">{data.display_name}</h3>
            <!-- <p>{JSON.stringify(data)}</p> -->
            <p><a class="uk-button uk-button-default uk-button-small uk-align-right">標本</a></p>
          </div>
        </div>
      {/each}
    </div>
  </li>
  <li>
    <div class="uk-child-width-1-2@s uk-grid-match" uk-grid>
      {#each $ftsResults.field_number as data, i}
        <div>
          <div class="uk-card uk-card-hover uk-card-default uk-card-small uk-card-body">
            <h3 class="uk-card-title">{data.collector} {data.field_number}</h3>
            <p>採集日期: {data.collect_date}</p>
            <p>鑒定: </p>
            <p><a class="uk-button uk-button-default uk-button-small uk-align-right">標本</a></p>
          </div>
        </div>
      {/each}
    </div>
  </li>
  <li>
    <div class="uk-child-width-1-2@s uk-grid-match" uk-grid>
      {#each $ftsResults.accession_number as data, i}
        <div>
          <div class="uk-card uk-card-hover uk-card-default uk-card-small uk-card-body">
            <h3 class="uk-card-title">HAST:{data.accession_number}</h3>
            <p>{JSON.stringify(data.record)}</p>
            <!-- <p>{JSON.stringify(data)}</p> -->
            <p><a class="uk-button uk-button-default uk-button-small uk-align-right">標本</a></p>
          </div>
        </div>
      {/each}
    </div>
  </li>
</ul>
{/if}
