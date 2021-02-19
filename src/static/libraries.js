
var tagnames;
var scrollingEnabled = true;
var storeScrolling = false;

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

   /*
   let previousScroll = window.sessionStorage.getItem( folderID.toString + '/scroll' );
   if( previousScroll ) {
      console.log( 'scrolling back to ' + previousScroll.toString() )
      $(window).animate( {
         scrollTop: previousScroll
      } );
   }
   */

   // Setup XSRF for AJAX requests.
   $.ajaxSetup( {
      beforeSend: function( xhr, settings ) {
         if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test( settings.type ) && !this.crossDomain) {
            xhr.setRequestHeader( "X-CSRFToken", csrfToken );
         }
      }
   } );
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
      } )
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

   // Store the new postion for reuse on page load.
   if( storeScrolling ) {
      window.sessionStorage.setItem( folderID.toString + '/scroll', $(window).scrollTop() );
   }

   /* if( 'search' == op ) {
      query_str = '?csrf_token=' + csrfToken + '&keywords=' + encodeURI( keywords );
   } */

   page += 1;
   let pageRE = new RegExp( '%page%', 'g' );
   let folderIDRE = new RegExp( '%folder%', 'g' );
   let loadURL = scrollURL.replace( pageRE, page.toString() ).replace( folderIDRE, folderID.toString() );
   let scrollObject = {
      url: loadURL,
      method: scrollMethod
   };
   if( 'POST' == scrollMethod ) {
      scrollObject.data = scrollDataCallback();
   } else {
      scrollObject.url += '?' + scrollArgsCallback();
   }

   // Grab the next [loadIncrement] columns and append them to the table.
   $.ajax( scrollObject ).done( function( data ) {
      for( var i = 0 ; data.length > i ; i++ ) {
         let element = $(data[i]);
         console.log( 'element ' + i.toString() );
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
      
      $('#modal-form-rename #tags').tagsinput( {
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

      $('#modal-form-rename #id').val( id );
      $('#modal-form-type').text( item_data['check']['type'] );
      $('#modal-form-type').attr( 'class',
         'ok' == item_data['check']['status'] ? 
         'text-success' : 'text-danger' );
      $('#modal-form-rename #tags').tagsinput( 'removeAll' );
      for( const tag_idx in item_data['tags'] ) {
         $('#modal-form-rename #tags').tagsinput(
               'add', item_data['tags'][tag_idx] );
      }
      $('#modal-form-rename #name').val( item_data['name'] );
      $('#modal-form-rename #comment').val( item_data['comment'] );
      //var img_preview_tag = $('<img src="' + flaskRoot + 'preview/' + 
      //   data['id'] + '/360/270" class="" style="display: none;" />');
      var img_preview_tag = $('<img src="' + flaskRoot + 'preview/' +
         item_data['id'] +
         '/230/172" class="d-block w-100" style="display: none;" />');
      $('#modal-form-preview-img').empty();
      $('#modal-form-preview-img').append( img_preview_tag );
      $('#modal-form-preview-img img').one( 'load', function( e ) {
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

function clearDynamicPage() {
   // Disable folderID since we're now a fully dynamic page.
   folderID = -1;
   $('#libraries-folders .libraries-folders-inner').empty();
   $('#folder-items').empty();
   //$('#page-title').text( '' );
}
