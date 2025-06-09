import bpy, os

from .. utility import util

def create_rust_file(classname):

    sources_path = util.get_sources_path()
    filename = os.path.join(sources_path, classname) + ".rs"

    template = '''use bevy::prelude::*;

#[derive(Component)]
pub struct {class_name}Module {{
    pub number: f32,
}}

fn {class_name}_system(mut query: Query<(&{class_name}Module)>) {{
}}

pub fn register_{class_name}(app: &mut App) {{
    app.add_systems(Update, {class_name}_system);
}}

pub fn attach_{class_name}(entity: Entity, commands: &mut Commands) {{
    commands.entity(entity).insert({class_name}Module {{ number: 1.0 }});
}}
    '''

    formatted_template = template.format(class_name=classname)

    with open(filename, 'w') as f:
        f.write(formatted_template)

    return True