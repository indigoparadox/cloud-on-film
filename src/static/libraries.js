
var tagnames;
var scrollingEnabled = true;

(function( $ ) {

$().ready( function() {

   $('.card').enableThumbnailCard();

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

 $.fn.enableThumbnailCard = function() {

   // Enable image fade-in on load.
   $(this)
      .find( '.libraries-thumbnail-wrapper' )
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
    
   $(this)
      .find( 'a.thumbnail' )
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
}

$(window).on( 'scroll', function( e ) {
   let bottomPosition = $(document).height() - (3 * $(window).height());

   if( $(window).scrollTop() < bottomPosition || !scrollingEnabled ) {
      // We're not at the bottom or scrolling is disabled.
      return;
   }

   // Disable scrolling until get is finished.
   scrollingEnabled = false;

   /* if( 'search' == op ) {
      query_str = '?csrf_token=' + csrfToken + '&keywords=' + encodeURI( keywords );
   } */

   page += 1;
   let loadURL = flaskRoot + 'ajax/html/items/' + folderID.toString() + '/' + page.toString();
   // Grab the next [loadIncrement] columns and append them to the table.
   $.get( loadURL, function( data ) {
      for( var i = 0 ; data.length > i ; i++ ) {
         let element = $(data[i]);
         $('#folder-items').append( element );
         $(element).enableThumbnailCard();
      }

      // Re-enable scrolling after get is finished.
      if( 0 < data.length ) {
         scrollingEnabled = true;
      }
   } );
} );

}( jQuery ));

function renameItem( id ) {

   $.getJSON( flaskRoot + 'ajax/item/' + id.toString() + '/json', function( item_data ) {
      console.log( item_data );
      
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
      for( const tag_idx in item_data['_tags'] ) {
         $('#modal-input-tags').tagsinput( 'add', item_data['_tags'][tag_idx] );
      }
      $('#modal-input-name').val( item_data['name'] );
      $('#modal-input-comment').val( item_data['comment'] );
      //var img_preview_tag = $('<img src="' + flaskRoot + 'preview/' + 
      //   data['id'] + '/360/270" class="" style="display: none;" />');
      var img_preview_tag = $('<img src="' + flaskRoot + 'preview/' +
         item_data['id'] + '/230/172" class="" style="display: none;" />');
      $('#modal-form-preview').empty();
      $('#modal-form-preview').append( img_preview_tag );
      $('#modal-form-preview img').one( 'load', function( e ) {
         $(this).fadeIn();
      } );

      $('#modal-input-move').jstree( {
         core: {
            data: {
               url: flaskRoot + 'ajax/folders',
               data: function( node ) {
                  return {  id: node.id };
               }
            }
         }
      } ).bind( 'loaded.jstree', function( e, tree_data ) {
         // Open the root first.
         tree_data.instance.open_node( tree_data.instance.element.find( '#root' ) );

         // Iterate through current item's parents starting from the root.
         for( parent_idx in item_data['parents'] ) {
            parent_id = item_data['parents'][parent_idx];

            // Try to find the current parent in the tree's loaded nodes and open it.
            tree_data.instance.element.find( 'li' ).each( function( i ) {
               //console.log( 'looking for: ' + parent_id );
               //console.log( 'found: ' + $(this).attr( 'id' ) );
               if( $(this).attr( 'id' ) == parent_id ) {
                  tree_data.instance.open_node( $(this) );
               }
            } );

            //tree_data.instance.select_node( tree_data.instance.element.find( '#' + item_data['folder_id'].toString() ) );
         }
      } );

      $('#editModal').modal( 'show' );
   } );

   return false;
}

function saveRename() {

   var id = $('#modal-id').val();
   $.ajax( {
      url: flaskRoot + 'ajax/item/' + id.toString() + '/save',
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