 let grid = new w2grid({
   name: 'grid',
   box: '#grid',
   header: 'List of Names',
   reorderRows: false,
   show: {
     header: true,
     footer: true,
     toolbar: true,
     lineNumbers: true
   },
   columns: [
     { field: 'recid', text: 'ID', size: '30px' },
     { field: 'fname', text: 'First Name', size: '30%' },
     { field: 'lname', text: 'Last Name', size: '30%' },
     { field: 'email', text: 'Email', size: '40%' },
     { field: 'sdate', text: 'Start Date', size: '120px' }
   ],
   searches: [
     { type: 'int',  field: 'recid', label: 'ID' },
     { type: 'text', field: 'fname', label: 'First Name' },
     { type: 'text', field: 'lname', label: 'Last Name' },
     { type: 'date', field: 'sdate', label: 'Start Date' }
   ],
 })

console.log(GRID_INFO);
