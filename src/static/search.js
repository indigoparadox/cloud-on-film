
var searchSubmitTimer = null;

function onSearchSubmit() {
    $('#search-query #page').val( page.toString() );
    return $('#search-query').serialize();
}

function enableSearchScroll() {
    scrollURL = flaskRoot + 'ajax/html/search';
    scrollDataCallback = onSearchSubmit;
    scrollMethod = 'POST';
}

function searchSubmit() {
    console.log( 'submitting search...' );
    page = 0; // Starting a new search.
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

            enableSearchScroll();
    
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
