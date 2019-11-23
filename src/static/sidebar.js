
var sidebarStatus = 0;

$().ready( function() {
   $('#sidebar-toggle')
      .css( {
         'background-image': 'url( ' + flaskRoot + 'static/arrow-right-32.png )',
         'display': 'block'
      } )
      .click( function( e ) { sidebarToggle(); e.preventDefault() } );
   $('#sidebar-inner').hide();
   $('#sidebar').css( 'width', '32px' );
} )

function sidebarOpen() {
   $('#sidebar-inner').fadeIn();
   $('#sidebar-toggle').css( 'background-image', 'url( ' + flaskRoot + 'static/arrow-left-32.png )' );
   $("#sidebar").animate( { 'width': '120px' } );
   $("#main").animate( { 'margin-left': '120px' } );
   sidebarStatus = 1;
}

function sidebarClose() {
   $('#sidebar-inner').fadeOut();
   $('#sidebar-toggle').css( 'background-image', 'url( ' + flaskRoot + 'static/arrow-right-32.png )' );
   $("#sidebar").animate( { 'width': '32px' } );
   $("#main").animate( { 'margin-left': '0' } );
   sidebarStatus = 0;
} 

function sidebarToggle() {
   if( !sidebarStatus ) {
      // Sidebar is closed.
      sidebarOpen();
   } else {
      // Sidebar is open.
      sidebarClose();
   }
} 