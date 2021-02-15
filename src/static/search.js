
var searchSubmitTimer = null;

function searchSubmit() {
    console.log( 'submitting search...' );
}

$(document).ready( function() {
    $('#search-query-input').on( 'keypress', function( e ) {
        if( null != searchSubmitTimer ) {
            window.clearTimeout( searchSubmitTimer );
            searchSubmitTimer = null;
        }

        searchSubmitTimer = window.setTimeout( searchSubmit, 3000 );
    } );
} );
