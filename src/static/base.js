
function promptModal( text, callback, data ) {
    $('#promptModal').modal( 'show' );
    $('#promptModal p').html( text );
    $('#promptModal .btn-primary').data( 'userdata', data );
    $('#promptModal .btn-primary').on( 'click', callback );
}
