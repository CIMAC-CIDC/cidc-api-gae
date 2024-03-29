"""empty message

Revision ID: aa8a94b8e115
Revises: 08591dac6d5c
Create Date: 2019-10-02 16:55:20.360069

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "aa8a94b8e115"
down_revision = "08591dac6d5c"
branch_labels = None
depends_on = None


def upgrade():
    # this will delete all but the most recently-updated downloadable_files record for each object_url
    op.execute(
        """
        DELETE from 
        	downloadable_files 
        where 
        	id in (
	        	select 
	        		id 
	        	from 
	        		downloadable_files d 
	        	join 
		        	(
		        		select 
		        			max(_updated),
		        			object_url 
		        		from 
		        			downloadable_files 
		        		group by 
		        			object_url
		        		having 
		        			count(*) > 1
		        	) gm 
	        	on 
	        		gm.object_url = d.object_url 
	        		and 
	        		d._updated != gm.max
        		)
        """
    )
    # ### commands auto generated by Alembic###
    op.create_index(
        op.f("ix_downloadable_files_object_url"),
        "downloadable_files",
        ["object_url"],
        unique=True,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f("ix_downloadable_files_object_url"), table_name="downloadable_files"
    )
    # ### end Alembic commands ###
