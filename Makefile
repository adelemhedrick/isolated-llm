
up: .FORCE
	docker-compose up --build

down: .FORCE
	docker-compose down

ps: .FORCE
	docker-compose ps

.FORCE:




