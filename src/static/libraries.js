
var tagnames;

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

      // Setup tags autocomplete.
      tagnames = new Bloodhound({
         datumTokenizer: function( d ) {
            var tokens = d.name.split( /[\s\/]+/ );
            //console.log( tokens );
            return tokens;
         },
         queryTokenizer: Bloodhound.tokenizers.whitespace,
         prefetch: {
            url: flaskRoot + 'ajax/tags.json',
            filter: function( list ) {
               return $.map( list, function( tagname ) {
                  return { name: tagname }; 
               } );
            }
         }
      });

      tagnames.clearPrefetchCache();
      tagnames.initialize();
 } );

function renameItem( id ) {

   $.getJSON( flaskRoot + 'ajax/items/' + id.toString() + '/json', function( data ) {
      console.log( data );
      
      $('#modal-input-tags').tagsinput( {
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

      $('#modal-id').val( id );
      $('#modal-input-tags').tagsinput( 'removeAll' );
      for( const tag_idx in data['tags'] ) {
         $('#modal-input-tags').tagsinput( 'add', data['tags'][tag_idx] );
      }
      $('#modal-input-name').val( data['display_name'] );
      var img_preview_tag = $('<img src="' + flaskRoot + 'preview/' + data['id'] + '" class="" style="display: none;" />');
      $('#modal-form-preview').empty();
      $('#modal-form-preview').append( img_preview_tag );
      $('#modal-form-preview img').one( 'load', function( e ) {
         $(this).fadeIn();
      } );

      $('#editModal').modal( 'show' );
   } );

   return false;
}

function saveRename() {

   var id = $('#modal-id').val();
   $.ajax( {
      url: flaskRoot + 'ajax/items/' + id.toString() + '/save',
      /* data: {
         'tags': $('#modal-input-tags > input').tagsinput( 'items' )
      }, */
      data: $('#modal-form-rename').serialize(),
      type: 'POST',
      success: function( data ) {
         console.log( data );
         $('#editModal').modal( 'hide' );
      }
   } );

   return false;
}
