
var tagnames;
var scrollingEnabled = true;
var storeScrolling = false;
var selectedItems = [];

(function( $ ) {

$().ready( function() {

   $('.card').enableThumbnailCard();

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
         $('#folder-items').append( element );
         element.enableThumbnailCard();
      }

      recreateItemSpacers();

      // Re-enable scrolling after get is finished.
      if( 0 < data.length ) {
         scrollingEnabled = true;
      }
   } );
} );

}( jQuery ));

function clearDynamicPage() {
   // Disable folderID since we're now a fully dynamic page.
   folderID = -1;
   $('#libraries-folders .libraries-folders-inner').empty();
   $('#folder-items').empty();
   //$('#page-title').text( '' );
}

function recreateItemSpacers() {
   // Remove and re-insert the spacers after the new items.
   $('#folder-items .card-h-spacer').remove();
   for( let i = 0 ; 20 > i ; i++ ) {
      $('#folder-items').append( '<div class="card-h-spacer"></div>' );
   }
}
