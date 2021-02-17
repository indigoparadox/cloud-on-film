
var searchSubmitTimer = null;

function searchSubmit() {
    console.log( 'submitting search...' );
    $('#search-query #page').val( page.toString() );
    $.ajax( {
        url: flaskRoot + 'ajax/html/search',
        /* data: {
            'tags': $('#modal-input-tags > input').tagsinput( 'items' )
        }, */
        data: $('#search-query').serialize(),
        type: 'POST',
        success: function( data ) {
            console.log( data );

            clearDynamicPage();

            for( var i = 0 ; data.length > i ; i++ ) {
                let element = $(data[i]);
                $('#folder-items').append( element );
                $(element).enableThumbnailCard();
            }

            scrollURL = flaskRoot + 'ajax/html/search';
            scrollDataCallback = function() {
                $('#search-query #page').val( page.toString() );
                return $('#search-query').serialize();
            }
            scrollMethod = 'POST';
    
            // Re-enable scrolling after get is finished.
            /* if( 0 < data.length ) {
                scrollingEnabled = true;
            } else {
                scrollingEnabled = false;
            } */
        }
    } );
}

$(document).ready( function() {
    $('#search-query #query').on( 'keyup', function( e ) {
        if( null != searchSubmitTimer ) {
            window.clearTimeout( searchSubmitTimer );
            searchSubmitTimer = null;
        }

        searchSubmitTimer = window.setTimeout( searchSubmit, 3000 );
    } );
} );
