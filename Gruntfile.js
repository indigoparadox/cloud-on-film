
module.exports = function( grunt ) {

   var env = grunt.option( 'env' ) || 'std';
   var static_dir = 'src/static/';

   if( 'docker' == env ) {
      static_dir = 'app/static/';
   }

   grunt.initConfig( {
      concat: {
         jqueryuijs: {
            files: [{
               src: [
                  //'node_modules/jquery-ui/ui/jquery-1-7.js',
                  'node_modules/jquery-ui/ui/widget.js',
                  'node_modules/jquery-ui/ui/widgets/mouse.js',
                  'node_modules/jquery-ui/ui/unique-id.js',
                  'node_modules/jquery-ui/ui/data.js',
                  //'node_modules/jquery-ui/ui/effect.js',
                  'node_modules/jquery-ui/ui/plugin.js',
                  'node_modules/jquery-ui/ui/safe-active-element.js',
                  'node_modules/jquery-ui/ui/safe-blur.js',
                  'node_modules/jquery-ui/ui/scroll-parent.js',
                  'node_modules/jquery-ui/ui/version.js',
                  //'node_modules/jquery-ui/ui/keycode.js',
                  //'node_modules/jquery-ui/ui/labels.js',
                  //'node_modules/jquery-ui/ui/position.js',
                  //'node_modules/jquery-ui/ui/scroll-parent.js',
                  //'node_modules/jquery-ui/ui/tabbable.js',
                  //'node_modules/jquery-ui/ui/form-reset-mixin.js',
                  //'node_modules/jquery-ui/ui/effects/*.js',
                  //'node_modules/jquery-ui/ui/widgets/accordion.js',
                  //'node_modules/jquery-ui/ui/widgets/autocomplete.js',
                  //'node_modules/jquery-ui/ui/widgets/button.js',
                  //'node_modules/jquery-ui/ui/widgets/checkboxradio.js',
                  //'node_modules/jquery-ui/ui/widgets/controlgroup.js',
                  //'node_modules/jquery-ui/ui/widgets/datepicker.js',
                  //'node_modules/jquery-ui/ui/widgets/dialog.js',
                  'node_modules/jquery-ui/ui/widgets/draggable.js',
                  //'node_modules/jquery-ui/ui/widgets/droppable.js',
                  //'node_modules/jquery-ui/ui/widgets/menu.js',
                  //'node_modules/jquery-ui/ui/widgets/progressbar.js',
                  //'node_modules/jquery-ui/ui/widgets/resizable.js',
                  //'node_modules/jquery-ui/ui/widgets/selectable.js',
                  //'node_modules/jquery-ui/ui/widgets/selectmenu.js',
                  //'node_modules/jquery-ui/ui/widgets/slider.js',
                  //'node_modules/jquery-ui/ui/widgets/sortable.js',
                  //'node_modules/jquery-ui/ui/widgets/spinner.js',
                  //'node_modules/jquery-ui/ui/widgets/tabs.js',
                  //'node_modules/jquery-ui/ui/widgets/tooltip.js'
               ],
               dest: 'node_modules/jquery-ui/dist/jquery-ui.js'
            }]
         }
      },
      copy: {
         main: {
            files: [ {
               expand: true, src: [
                  'node_modules/jquery/dist/jquery.min.js',
                  'node_modules/bootstrap/dist/js/bootstrap.min.js',
                  'node_modules/bootstrap-tagsinput/dist/bootstrap-tagsinput.min.js',
                  'node_modules/bootstrap-tagsinput/dist/bootstrap-tagsinput.css',
                  'node_modules/typeahead.js/dist/typeahead.bundle.min.js',
                  'node_modules/bootstrap/dist/css/bootstrap.min.css',
                  'node_modules/popper.js/dist/umd/popper.min.js',
                  'node_modules/unveil2/dist/jquery.unveil2.min.js',
                  'node_modules/featherlight/release/featherlight.min.css',
                  'node_modules/featherlight/release/featherlight.min.js',
                  'node_modules/featherlight/release/featherlight.gallery.min.css',
                  'node_modules/featherlight/release/featherlight.gallery.min.js',
                  'node_modules/jquery-ui/dist/jquery-ui.js',
                  'node_modules/jstree/dist/jstree.min.js',
               ], dest: static_dir, flatten: true },
               {expand: true, src: [
                  'node_modules/jstree/dist/themes/default-dark/*',
               ], dest: static_dir + '/default-dark', flatten: true },
            ]
         }
      },
      uglify: {
         jqueryuijs: {
            files: [{
               src: [
                  'node_modules/jquery-ui/dist/jquery-ui.js'
               ],
               ext: '.min.js',
               flatten: true,
               expand: true,
               dest: static_dir 
            }]
         }
      },
      cssmin: {
         jqueryuicss: {
            files: [{
               src: [
                  //'node_modules/jquery-ui/dist/jquery-ui.base.css'
                  'node_modules/jquery-ui/themes/base/base.css'
               ],
               ext: '.min.css',
               flatten: true,
               expand: true,
               dest: static_dir 
            }]
         }
      }
   } )

   grunt.loadNpmTasks( 'grunt-contrib-copy' );
   grunt.loadNpmTasks( 'grunt-contrib-concat' );
   grunt.loadNpmTasks( 'grunt-contrib-uglify' );
   grunt.loadNpmTasks( 'grunt-contrib-cssmin' );

   grunt.registerTask( 'default', ['copy', 'concat', 'uglify', 'cssmin'] );
};

