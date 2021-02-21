
var tagnames;
var scrollingEnabled = true;
var storeScrolling = false;
var selectedItems = [];

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

   $(this)
      .find( '.item-checkbox' )
      .fadeIn()
      .on( 'change', function( e ) {
         if( this.checked ) {
            selectedItems.push( $(this).attr( 'id' ) );
         } else {
            let idx = selectedItems.indexOf( $(this).attr( 'id' ) );
            selectedItems.splice( idx, 1 );
         }

         if( 0 == selectedItems.length ) {
            $('#form-edit-checked-items').slideUp();
         } else {
            $('#form-edit-checked-items').slideDown();
         }

         console.log( selectedItems );
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

   $('#editModal').on( 'hidden.bs.modal', function( e ) {
      $('#modal-input-move').jstree().destroy();
      $('#modal-input-move').empty();
   } );

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

   $.getJSON( flaskRoot + 'ajax/item/' + id.toString() + '/json',
   function( itemData ) {
      console.log( itemData );
      
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
      $('#modal-form-type').text( itemData['check']['type'] );
      $('#modal-form-type').attr( 'class',
         'ok' == itemData['check']['status'] ? 
         'text-success' : 'text-danger' );
      $('#modal-form-rename #tags').tagsinput( 'removeAll' );
      for( const tag_idx in itemData['tags'] ) {
         $('#modal-form-rename #tags').tagsinput(
               'add', itemData['tags'][tag_idx] );
      }
      $('#modal-form-rename #name').val( itemData['name'] );
      $('#modal-form-rename #comment').val( itemData['comment'] );
      //var img_preview_tag = $('<img src="' + flaskRoot + 'preview/' + 
      //   data['id'] + '/360/270" class="" style="display: none;" />');
      var img_preview_tag = $('<img src="' + flaskRoot + 'preview/' +
      itemData['id'] +
         '/230/172" class="d-block w-100" style="display: none;" />');
      $('#modal-form-preview-img').empty();
      $('#modal-form-preview-img').append( img_preview_tag );
      $('#modal-form-preview-img img').one( 'load', function( e ) {
         $(this).fadeIn();
      } );

      let treeLoaded = $.Deferred();
      let treeLoadFinished = false;

      $('#modal-input-move').jstree( {
         core: {
            data: {
               url: flaskRoot + 'ajax/folders',
               data: function( node ) {
                  return {  id: node.id };
               }
            }
         }
      } );
      $('#modal-input-move').on( 'loaded.jstree', function( e, treeData ) {
         // Open the root first.
         let rootNode = treeData.instance.element.find( '#root' );
         treeData.instance.open_node( rootNode );
      } );
      $('#modal-input-move').on( 'after_open.jstree', function( e, parentNode ) {
         if( treeLoadFinished ) {
            return;
         }

         // Iterate through current item's parents starting from the root.
         let parentIdx = 0;
         for( parentIdx in itemData['parents'] ) {
            parentID = itemData['parents'][parentIdx];

            // Try to find the current parent in the tree's loaded nodes and open it.
            parentNode.instance.element.find( '#' + parentID ).each( function( i ) {
               parentNode.instance.open_node( $(this) );
               if( parentIdx == itemData['parents'].length - 1 ) {
                  // Last parent should be visible, now.
                  treeLoaded.resolve( parentNode, this );
               }
            } );
         }
      } );

      $('#editModal').modal( 'show' );

      $.when( treeLoaded ).done( function( parentNode, node ) {
         // All parents are loaded, so select the last one.
         parentNode.instance.deselect_all();
         parentNode.instance.select_node( node, true );
         console.assert( 1 == parentNode.instance.get_selected( true ).length );
         treeLoadFinished = true;
      } );
   } );

   return false;
}

function saveRename() {

   let moveSelected = $('#modal-input-move').jstree( 'get_selected', true )[0];
   console.log( $('#modal-input-move').jstree( 'get_selected', true ) );
   // Build the path using IDs, as those are simpler to parse server-side.
   let movePath = $('#modal-input-move').jstree().get_path( moveSelected, '/', true );
   $('#modal-form-rename #location').val( movePath );
   
   $.ajax( {
      url: flaskRoot + 'ajax/item/save',
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
