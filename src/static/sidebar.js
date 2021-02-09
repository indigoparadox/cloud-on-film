
var sidebarStatus = 0;

$().ready( function() {
   $('#sidebar-toggle')
      .css( {
         'background-image': 'url( ' + flaskRoot + 'static/arrow-right-32.png )',
         'display': 'block'
      } )
      .click( function( e ) { sidebarToggle(); e.preventDefault() } );
   
   var sidebarWidth = localStorage.getItem( 'sidebarWidth' );
   if( null == sidebarWidth ) {
      sidebarWidth = 120;
      localStorage.setItem( 'sidebarWidth', sidebarWidth );
   }
   
   $('#sidebar-inner').hide();
   $('#sidebar').css( 'width', '32px' );
   if( localStorage.getItem( 'sidebarStatus' ) ) {
      sidebarOpen();
   }

   var resizeOffHandler = function( e ) {
      //console.log( e );
      $('#sidebar-resize').data( 'dragging', false );
   };

   $('#sidebar-resize').on( 'mouseleave', resizeOffHandler );
   $('#sidebar-resize').on( 'mouseup', resizeOffHandler );

   $('#sidebar-resize').on( 'mousemove', function( e ) {
      if( $('#sidebar-resize').data( 'dragging' ) ) {
         var offset = e.offsetX - 2; // Center;
         sidebarResize( offset );
      }
   } );

   $('#sidebar-resize').on( 'mousedown', function( e ) {
      //console.log( e );
      $('body').on( 'mouseup', resizeOffHandler );
      $('#sidebar-resize').data( 'dragging', true );
      e.preventDefault();
   } );
} )

function sidebarAbsoluteSize( sidebarWidth ) {
   $("#sidebar").css( 'width', sidebarWidth.toString() + 'px' );
   $('#sidebar-resize').css( 'left', sidebarWidth.toString() + 'px' );
   $("#main").css( 'margin-left', (sidebarWidth + 32).toString() + 'px' );
}

function sidebarResize( offset ) {
   var sidebarWidth = parseInt( localStorage.getItem( 'sidebarWidth' ) );
   sidebarWidth += offset;
   localStorage.setItem( 'sidebarWidth', sidebarWidth );
   sidebarAbsoluteSize( sidebarWidth );
}

function sidebarOpen() {
   var sidebarWidth = parseInt( localStorage.getItem( 'sidebarWidth' ) );
   $('#sidebar-inner').fadeIn();
   $('#sidebar-resize').fadeIn();

   $('#sidebar-toggle').css( 'background-image', 'url( ' + flaskRoot + 'static/arrow-left-32.png )' );
   sidebarAbsoluteSize( sidebarWidth );
   //$("#sidebar").animate( { 'width': String( sidebarWidth ) + 'px' } );
   //$('#sidebar-resize').animate( { 'left': String( sidebarWidth ) + 'px' } );
   //$("#main").animate( { 'margin-left': String( sidebarWidth ) + 'px' } );
   
   sidebarStatus = 1;
   window.localStorage.setItem( 'sidebarStatus', 1 );
}

function sidebarClose() {
   $('#sidebar-inner').fadeOut();
   $('#sidebar-resize').hide();

   $('#sidebar-toggle').css( 'background-image', 'url( ' + flaskRoot + 'static/arrow-right-32.png )' );
   sidebarAbsoluteSize( 32 );
   //$("#sidebar").animate( { 'width': '32px' } );
   //$('#sidebar-resize').animate( { 'left': '32px' } );
   //$("#main").animate( { 'margin-left': '0' } );

   sidebarStatus = 0;
   window.localStorage.setItem( 'sidebarStatus', 1 );
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