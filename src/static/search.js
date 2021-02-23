
var searchSubmitTimer = null;

(function( $ ) {

$.fn.searchSubmitAJAX = function() {
    
    console.log( 'submitting search...' );
    page = 0; // Starting a new search.

    let formUUID = $(this).parents( 'form' ).attr( 'data-form-uuid' );
    let queryText = $('#' + formUUID + '-query').val();

    $('.search-query .page').val( page.toString() );
    $.ajax( {
        url: flaskRoot + 'ajax/html/search?query=' + encodeURIComponent( queryText ),
        type: 'GET',
        success: function( data ) {

            clearDynamicPage();

            for( var i = 0 ; data.length > i ; i++ ) {
                let element = $(data[i]);
                $('#folder-items').append( element );
                $(element).enableThumbnailCard();
            }

            recreateItemSpacers();
            scrollURL = flaskRoot + 'ajax/html/search';
            scrollArgsCallback = searchArgs;
            scrollArgsCaller = this;
            scrollMethod = 'GET';
    
            // Re-enable scrolling after get is finished.
            /* if( 0 < data.length ) {
                scrollingEnabled = true;
            } else {
                scrollingEnabled = false;
            } */
        }
    } );
}

}( jQuery ));

/* function onSearchSubmit() {
    $('.search-query .page').val( page.toString() );
    return $('#search-query').serialize();
} */

function searchArgs( element ) {
    return 'query=' + $(element).val() + '&page=' + page.toString();
}

var searchCallerElement = null;

$(document).ready( function() {
    $('.search-query .query').on( 'keyup', function( e ) {
        if( null != searchSubmitTimer ) {
            window.clearTimeout( searchSubmitTimer );
            searchSubmitTimer = null;
        }

        // Need a wrapper to remember which form we're coming from.
        let searchCaller = function() {
            $(searchCallerElement).searchSubmitAJAX();
        };
        searchCallerElement = this;

        searchSubmitTimer = window.setTimeout( searchCaller, 1500 );
    } );
} );

function promptDeleteSearch( name, id ) {
    promptModal(
        'Are you sure you wish to delete the saved search "' + name +
            '"? This action cannot be undone.',
        confirmDeleteSearch,
        id,
        DialogTypes.YESNO
    );
    return false;
}

function confirmDeleteSearch( e, id ) {
    $.ajax( {
        url: flaskRoot + 'ajax/search/delete',
        data: { 'id': id, 'csrf_token': csrfToken },
        type: 'POST',
        success: function( data ) {
            console.log( data );
            if( 'success' == data['submit_status'] ) {
                promptModal(
                    'Saved search successfully deleted.',
                    function( e, data ) { window.location = flaskRoot; },
                    null,
                    DialogTypes.OKONLY
                );
            } else {
                promptModal(
                    'Problem deleting saved search.',
                    promptModalHide,
                    null,
                    DialogTypes.OKONLY
                );
            }
        }
    } );
}
