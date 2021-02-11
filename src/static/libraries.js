
$().ready( function() {
   $('.libraries-thumbnail-wrapper')
      .on( 'loading.unveil', function() {
         $(this).css( 'opacity', '0' );
      } )
      .on( 'loaded.unveil', function() {
         $(this).animate( { 'opacity': '1' } );
      } )
      .unveil( {
         'offset': 200,
         'debug': true,
         //'placeholder': "{{ url_for( 'static', filename='art-palette-72.png' ) }}"
      } );
    
   $('a.thumbnail')
      .each( function( elem ) {
         $(this).attr( 'href', $(this).data( 'fullsize' ) );
      } )
      .featherlightGallery( {
         'type': 'image',
         'previousIcon': '<img src="' + flaskRoot +
            'static/arrow-left-64.png" alt="Previous" />',
         'nextIcon': '<img src="' + flaskRoot + 
            'static/arrow-right-64.png" alt="Next" />',
      } );
 } );

function renameItem( id ) {

   $.getJSON( flaskRoot + 'ajax/items/' + id.toString() + '.json', function( data ) {
      console.log( data );

      // Setup tags autocomplete.
      var tagnames = new Bloodhound({
         datumTokenizer: Bloodhound.tokenizers.obj.whitespace( 'name' ),
         queryTokenizer: Bloodhound.tokenizers.whitespace,
         prefetch: {
            url: flaskRoot + 'ajax/tags.json',
            filter: function( list ) {
               return $.map( list, function( tagname ) {
                  return { name: tagname }; });
            }
         }
      });
      tagnames.initialize();
      
      $('#modal-input-tags > input').tagsinput( {
         tagClass: function( name ) {
            return 'bg-dark';
         },
         typeaheadjs: {
            name: 'tagnames',
            displayKey: 'name',
            valueKey: 'name',
            source: tagnames.ttAdapter()
         }
      } );

      $('#modal-input-tags > input').tagsinput( 'removeAll' );
      for( const tag_idx in data['tags'] ) {

         $('#modal-input-tags > input').tagsinput( 'add', data['tags'][tag_idx] );
   
         $('#editModal').modal( 'show' );
      }
   } );

   return false;
}
