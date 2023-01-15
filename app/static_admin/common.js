 UIkit.util.on('.item-delete-confirm', 'click', function (e) {
   e.preventDefault();
   e.target.blur();
   UIkit.modal.confirm('確定要刪除?').then(function () {
     fetch(e.target.dataset.deleteurl, { method: 'DELETE' })
            .then(resp => resp.json())
            .then(json => {
              //console.log('ok', json);
              if ('next_url' in json) {
                location.href = json.next_url;
              }});
   }, function () {
     // console.log('Rejected.')
   });
 });
