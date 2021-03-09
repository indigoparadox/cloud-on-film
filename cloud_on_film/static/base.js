
const DialogTypes = {
    YESNO: ['Yes', 'No'],
    OKCANCEL: ['OK', 'Cancel'],
    OKONLY: ['OK']
}

function promptModalHide( e, data=null ) {
    $('#promptModal').modal( 'hide' );
}

function promptModal( text, callback, data, dialogType=DialogTypes.OKCANCEL ) {

    $('#promptModal').modal( 'show' );
    $('#promptModal p').html( text );

    if( DialogTypes.OKONLY == dialogType ) {
        $('#promptModal .btn-secondary').hide();
        $('#promptModal .btn-primary').show();
        $('#promptModal .btn-primary').text( dialogType[0] );
    } else {
        $('#promptModal .btn-secondary').show();
        $('#promptModal .btn-secondary').text( dialogType[1] );
        $('#promptModal .btn-primary').show();
        $('#promptModal .btn-primary').text( dialogType[0] );
    }

    // Cancel/No
    $('#promptModal .btn-secondary').off( 'click' );
    $('#promptModal .btn-secondary').on( 'click', promptModalHide );

    // OK/Yes
    $('#promptModal .btn-primary').off( 'click' );
    $('#promptModal .btn-primary').on( 'click', function( e ) {
        callback( e, data );
    } );
}
