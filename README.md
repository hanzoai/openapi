# swagger
Swagger API Blueprints for the Hanzo APIs.

## Organization
Each Hanzo API is broken down into an individual YAML file and organized into
high-level collections. Our build process stitches these together so it's easy
to create a single YAML file for a given set of APIs.

## Adding a new set of APIs
A new set of APIs can be declared in the Sakefile, with id set to `false`. After
the API is published, add the returned id to the Sakefile to ensure it continues
to be synced on subsequent publishes.
